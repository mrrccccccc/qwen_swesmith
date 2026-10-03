"""Local validation comparison, not an official task-execution benchmark.
Place this file beside run.py; Windows and Linux use the same command.
"""
from __future__ import annotations
import argparse
import csv
import gc
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    use_current = "--current-python" in sys.argv
    if use_current:
        sys.argv.remove("--current-python")
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not use_current and python.is_file() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise SystemExit(subprocess.call([str(python), "-u", str(Path(__file__).resolve()), *sys.argv[1:]]))
    if not (ROOT / "src" / "qwen_swesmith").is_dir():
        raise RuntimeError("Place evaluate_local.py beside the project's run.py")
    sys.path.insert(0, str(ROOT / "src"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3-0.6b")
    parser.add_argument("--max-records", type=int, default=20, help="Sample size for EACH validation file")
    parser.add_argument("--max-windows-per-record", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if args.max_records < 1 or args.max_windows_per_record < 1:
        parser.error("Sample limits must be positive")
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    from qwen_swesmith.common import config, path, rows, write_json, write_rows, file_hash, offline, seed_all
    offline()
    from qwen_swesmith.model import load, tokenizer
    from qwen_swesmith.encoding import encode_sft, encode_pair, sequence_logprob
    import torch
    profiles = config("configs/model_profiles.yaml")
    if args.model not in profiles:
        parser.error("Unknown model profile: " + args.model)
    profile = profiles[args.model]
    cfg = config(profile["sft"])
    dpo_cfg = config(profile["stage2"])
    if cfg["base_dir"] != dpo_cfg["base_dir"]:
        raise ValueError("SFT/DPO profile uses different base directories")
    out = path(args.output or "outputs/local_eval/" + args.model)
    if out.exists():
        raise FileExistsError("Evaluation directory exists; choose a new --output: " + str(out))
    adapters = {"base": None,
                "sft": str(path(cfg["output_dir"]) / "best_adapter"),
                "stage2": str(path(dpo_cfg["output_dir"]) / "best_adapter")}
    for variant, adapter in adapters.items():
        if adapter and not (Path(adapter) / "adapter_config.json").is_file():
            raise FileNotFoundError("Missing " + variant + " adapter: " + adapter)
    tok = tokenizer(cfg["base_dir"])
    rng = random.Random(args.seed)
    skips, selections, sft_examples, pair_examples = [], [], [], []
    sources = {"sft": cfg["val_file"], "dpo": dpo_cfg["val_file"]}
    for kind, filename in sources.items():
        records = list(rows(filename))
        rng.shuffle(records)
        for index, record in enumerate(records[:args.max_records]):
            key = record.get("sha256") or str(index)
            info = {"kind": kind, "record_id": key, "task_id": record.get("task_id"), "repo": record.get("repo")}
            try:
                if kind == "sft":
                    windows = encode_sft(tok, record, cfg)
                    if not windows:
                        raise ValueError("No supervised windows")
                    indices = sorted(rng.sample(range(len(windows)), min(len(windows), args.max_windows_per_record)))
                    for i in indices:
                        sft_examples.append((dict(info, window=i), windows[i]))
                    selections.append(dict(info, selected_windows=indices, total_windows=len(windows)))
                else:
                    encoded = encode_pair(tok, record, cfg)
                    pair_examples.append((info, encoded))
                    selections.append(info)
            except (ValueError, KeyError, TypeError) as e:
                skips.append(dict(info, reason=str(e)))
    if not sft_examples:
        raise ValueError("No usable SFT validation examples")
    out.mkdir(parents=True)
    write_rows(out / "selected_examples.jsonl", selections)
    write_rows(out / "skipped_examples.jsonl", skips)
    write_json(out / "protocol.json", {
        "evaluation_type": "local_validation_teacher_forcing", "official_benchmark": False,
        "model_profile": args.model, "seed": args.seed,
        "max_records_per_file": args.max_records, "max_windows_per_record": args.max_windows_per_record,
        "sequence_length": cfg["max_length"], "encoding_config": cfg,
        "validation_files": {k: {"path": str(path(v)), "sha256": file_hash(path(v))} for k, v in sources.items()},
        "adapters": adapters, "sft_windows": len(sft_examples), "dpo_pairs": len(pair_examples),
        "selection_rule": "Seeded sample without replacement, then uniformly sampled SFT windows; identical examples for all variants",
        "preference_rule": "chosen mean log-probability per supervised token > rejected mean log-probability; ties are not wins",
        "limitations": "Validation data, not an independent test set. No patch execution, judge, official benchmark or DPO reference rewards."
    })
    summary = []
    expected_identity = None
    for variant, adapter in adapters.items():
        print("[EVAL] Loading " + variant, flush=True)
        seed_all(args.seed)
        model, model_tok, details = load(cfg, adapter=adapter, train=False)
        identity = (details["base_repo"], details["base_revision"], details["chat_template_sha256"])
        if expected_identity is None:
            expected_identity = identity
        elif identity != expected_identity:
            raise ValueError("Base model or tokenizer provenance changed between variants")
        model.eval()
        torch.cuda.synchronize()
        started = time.perf_counter()
        total_nll, total_tokens, wins, ties, margins = 0.0, 0, 0, 0, []
        evidence = []
        with torch.inference_mode():
            for i, (info, example) in enumerate(sft_examples):
                lp, count = sequence_logprob(model, example)
                value = float(lp)
                if not math.isfinite(value):
                    raise ValueError("Non-finite validation log-probability")
                total_nll -= value
                total_tokens += count
                evidence.append(dict(info, logprob_sum=value, supervised_tokens=count, mean_nll=-value / count))
                if (i + 1) % 10 == 0:
                    print("[EVAL] " + variant + " SFT windows " + str(i + 1) + "/" + str(len(sft_examples)), flush=True)
            for info, pair in pair_examples:
                chosen_lp, chosen_n = sequence_logprob(model, pair["chosen"])
                rejected_lp, rejected_n = sequence_logprob(model, pair["rejected"])
                chosen, rejected = float(chosen_lp) / chosen_n, float(rejected_lp) / rejected_n
                if not math.isfinite(chosen) or not math.isfinite(rejected):
                    raise ValueError("Non-finite preference log-probability")
                margin = chosen - rejected
                wins += int(margin > 0)
                ties += int(margin == 0)
                margins.append(margin)
                evidence.append(dict(info, chosen_mean_logprob=chosen, rejected_mean_logprob=rejected,
                                     margin=margin, preferred_chosen=margin > 0))
        torch.cuda.synchronize()
        nll = total_nll / total_tokens
        result = {"variant": variant, "sft_windows": len(sft_examples), "supervised_tokens": total_tokens,
                  "validation_nll": nll, "validation_perplexity": math.exp(nll) if nll < 700 else None,
                  "dpo_pairs": len(pair_examples), "preference_accuracy": wins / len(pair_examples) if pair_examples else None,
                  "preference_ties": ties, "mean_preference_margin": sum(margins) / len(margins) if margins else None,
                  "scoring_seconds": time.perf_counter() - started}
        write_json(out / (variant + "_summary.json"), result)
        write_json(out / (variant + "_model_details.json"), details)
        write_rows(out / (variant + "_examples.jsonl"), evidence)
        summary.append(result)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        del model, model_tok
        gc.collect()
        torch.cuda.empty_cache()
    write_json(out / "summary.json", {"official_benchmark": False, "results": summary})
    with (out / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print("Finished: " + str(out), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileNotFoundError, FileExistsError, ModuleNotFoundError) as e:
        print("ERROR: " + str(e), file=sys.stderr)
        raise SystemExit(2)
