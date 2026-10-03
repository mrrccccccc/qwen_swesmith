# Qwen3.6 × SWE-smith：Windows / Linux 逐文件完整源码
跨平台更新：2026-10-03。统一 Python 入口 run.py，安装入口 setup_env.py；本次没有运行验证。
默认开发模式可以先做数据处理/训练；formal模式保留原题训练前冻结评测的要求。
24GB显存限制仍存在；完整官方vLLM和容器评测的Linux限制详见README。
## 文件目录
- `.gitignore`
- `QUICKSTART.md`
- `README.md`
- `benchmarks/manifest.json`
- `configs/data.yaml`
- `configs/data_formal.yaml`
- `configs/download.yaml`
- `configs/inference.yaml`
- `configs/sft_80gb.yaml`
- `configs/sft_formal.yaml`
- `configs/stage2_80gb.yaml`
- `configs/stage2_formal.yaml`
- `constraints_torch.txt`
- `data/README.md`
- `data/exclusion_policy.json`
- `docs/EVALUATION.md`
- `docs/HARDWARE.md`
- `docs/METHOD.md`
- `docs/SUBMISSION.md`
- `models/README.md`
- `pyproject.toml`
- `requirements.txt`
- `run.py`
- `scripts/download.sh`
- `scripts/evaluate_all.sh`
- `scripts/serve_vllm.sh`
- `scripts/train.sh`
- `setup_env.py`
- `src/qwen_swesmith/__init__.py`
- `src/qwen_swesmith/analysis.py`
- `src/qwen_swesmith/benchmarks.py`
- `src/qwen_swesmith/cli.py`
- `src/qwen_swesmith/common.py`
- `src/qwen_swesmith/data.py`
- `src/qwen_swesmith/download.py`
- `src/qwen_swesmith/encoding.py`
- `src/qwen_swesmith/export.py`
- `src/qwen_swesmith/inference.py`
- `src/qwen_swesmith/model.py`
- `src/qwen_swesmith/portable.py`
- `src/qwen_swesmith/preflight.py`
- `src/qwen_swesmith/schema.py`
- `src/qwen_swesmith/train.py`
- `tests/test_core.py`
- `tests/test_real_template.py`

## .gitignore

````text
.venv/
__pycache__/
*.pyc
.env
installation.json
assets/
outputs/
data/raw/
data/processed/
*.egg-info/

````

## QUICKSTART.md

````markdown
# Windows / Linux 最短启动说明

安装 Python 3.12，解压后在项目根目录打开终端。

Windows CMD / PowerShell：
```text
py -3.12 setup_env.py --cuda cu128
```

Linux：
```text
python3.12 setup_env.py --cuda cu128
```

之后两系统均执行：
```text
python run.py download
python run.py licenses
python run.py prepare
python run.py sft
python run.py stage2
python run.py curves --run-dir outputs/sft
python run.py curves --run-dir outputs/stage2
```

Windows没有python命令时，把python换成py即可。
入口自动使用项目虚拟环境，不用activate，不需要任何.sh脚本。
下载后训练和推理全部本地加载。

本地文本推理：
```text
python run.py serve --adapter outputs/stage2/best_adapter
```

默认是开发模式，不因未填的benchmark manifest阻塞；正式面试实验使用formal
配置并先冻结评测版本，完整流程在README。

24GB不能运行本项目BF16的35B基座；80GB是短窗口候选，H200 141GB更有余量。
原生Windows不支持官方vLLM CUDA后端，完整长上下文及官方容器评测需要Linux/
WSL2或Linux服务器。按要求，本次只修改代码和打包，没有运行验证。

````

## README.md

````markdown
# Qwen3.6 + SWE-smith：Windows / Linux 共用 Python 程序

主入口 `run.py`，安装入口 `setup_env.py`。下载、数据处理、SFT、DPO、曲线、
本地文本推理和 CPU 模型导出均由同一套 Python 代码调用，不依赖 Bash、
PowerShell 脚本、source、export、tee、chmod 或激活虚拟环境。
按用户要求，本次修改后未运行验证或 GPU 实验；跨平台代码不等于经过两系统实测。

## 硬件与系统范围

| 功能 | 原生 Windows | Linux |
|---|---|---|
| 模型/数据下载、许可查询、数据清洗、曲线 | Python 3.12 | Python 3.12 |
| SFT / DPO / 本地文本推理 | CUDA PyTorch；需足够显存 | CUDA PyTorch；需足够显存 |
| CPU 合并导出 | 足够主机内存 | 足够主机内存 |
| vLLM 正式长上下文服务 | 官方 CUDA 后端需 Linux/WSL2 | 使用独立 vLLM 环境 |
| 四项官方容器/Agent 评测 | 通过 Linux/WSL2 操作；不宣称全部框架原生支持 Windows | 安装对应官方框架并接入 |

**24GB 仍不能装下本项目 BF16 的 35B 基座。** 更换启动程序不会消除显存限制。
80GB 是短窗口候选，H200 141GB 更有余量；没有实机保证。
专家冻结、attention LoRA rank=8、micro batch=1、梯度累积16。
Windows 不强制安装 Linux 专用的 flash-attn、mamba-ssm、DeepSpeed 或 Triton；
模型采用 Transformers 的 PyTorch/SDPA 路线，缺少专用内核时速度可能明显下降。
实现依赖的第三方模型内核仍需在目标机器上实际确认。

## 1. 安装（只需一次）

安装 Python 3.12 和适合 GPU 的 NVIDIA 驱动。解压后进入项目根目录。

Windows CMD / PowerShell：
```text
py -3.12 setup_env.py --cuda cu128
```

Linux：
```text
python3.12 setup_env.py --cuda cu128
```

脚本自动创建项目内 `.venv`，安装 PyTorch 2.8.0 + torchvision 0.23.0 的官方
CUDA wheel、共享依赖和本项目，并写 dependencies.lock.txt。
cu126/cu128/cu129 可选，须与驱动兼容；--cuda cpu 仅用于数据处理。
requirements.txt 只列共享依赖，PyTorch 约束另存 constraints_torch.txt。

后面的入口自动选择 `.venv/Scripts/python.exe` 或 `.venv/bin/python`，
不需要 activate，也不受 PowerShell 脚本执行策略限制。
如果 Windows 没有 python 命令，下方命令把 python 换成 py 即可。

## 2. 完整下载模型和数据
```text
python run.py download
python run.py licenses
```

本地保存：
- assets/models/Qwen3.6-35B-A3B/：完整原权重、tokenizer、processor、配置。
- assets/datasets/SWE-smith/：任务表全部 parquet。
- assets/datasets/SWE-smith-trajectories/：原始轨迹全部 parquet。
- data/licenses.json：源仓库许可清单，UNKNOWN 默认排除。

下载固定 revision 并保存 SHA256；之后加载只接受本地目录，local_files_only=True，
Hub 离线。修改存储位置时，要同时更新下载和使用配置。
Windows YAML 路径推荐 D:/qwen_assets/...，或用单引号包裹反斜杠路径。
官方模型和数据 revision 保持上一版固定值，不在本次修改时更换。

## 3. 生成数据
```text
python run.py prepare
```

默认是明确标注的 **development 模式**，不会被未填写的官方 benchmark 配置阻塞。
默认 data/exclusion_policy.json 是空的开发排除清单，不意味着已证明无评测泄漏。
默认运行不能当作满足原题的正式面试实验。可填写开发排除仓库/任务/公开 prompt。
生成 sft_train/val、dpo_train/val、audit、stats、provenance 到 data/processed/。
轨迹使用 tool split；按 instance_id 关联；成功轨迹 SFT，同任务成功/失败补丁 DPO。
未知来源许可、无效轨迹、重复轨迹排除；同一仓库不跨训练/开发 split。

## 4. 两阶段训练
```text
python run.py sft --gpu 0
python run.py curves --run-dir outputs/sft
python run.py stage2 --gpu 0
python run.py curves --run-dir outputs/stage2
```

或用一条命令（重新处理数据并依次训练两阶段）：
```text
python run.py train-all --gpu 0
```

训练自动将 stdout/stderr 保存到 outputs/console，包含错误日志。
参数在 configs/sft_80gb.yaml、configs/stage2_80gb.yaml。
默认输出目录已使用时会报错，防止覆盖。重新实验请配置新的 output_dir，
相应更新 stage2 的 initial_adapter。
默认 SFT 500 optimizer steps、DPO 150 steps，是起步值而非实测最优。
SFT 使用2048 token重叠窗口；DPO超长pair排除并记录，数据不足会明确报错。
阶段二在 SFT best_adapter 上继续训练，冻结 SFT reference adapter，与 policy
共享基座；stage2 adapter 是完整更新后的 adapter。
无 optimizer-resume 功能，失败后用新运行目录重新训练。

输出：
- outputs/sft/best_adapter、final_adapter、定期 checkpoint。
- outputs/stage2/best_adapter、final_adapter、定期 checkpoint。
- config、启动命令、pip freeze、实际模型加载报告、LoRA目标、资源、loss、DEV结果。
- curves/：每项指标独立300dpi PNG、PDF和源CSV。

## 5. 本地文本推理（两系统同样命令）
```text
python run.py serve --gpu 0
```

上面加载 Base。停止服务后可以加载训练模型，同一时刻只启动一个服务：
```text
python run.py serve --gpu 0 --adapter outputs/sft/best_adapter
python run.py serve --gpu 0 --adapter outputs/stage2/best_adapter
```
接口 http://127.0.0.1:8000/v1/chat/completions。
服务只生成工具调用，由外部 Agent 执行工具。
默认 text-only、8192 context、1024 output budget，仅用于本地调试，不冒充
256K正式评测。SSE为缓冲兼容输出，不是逐token实时流。

## 6. CPU 导出（两系统同样命令）
```text
python run.py export --output assets/exports/base
python run.py export --adapter outputs/sft/best_adapter --output assets/exports/sft
python run.py export --adapter outputs/stage2/best_adapter --output assets/exports/stage2
```
主机内存建议128–192GB，保留视觉模块，MTP不启用；三版本保持同样导出方式。

## 7. 正式面试模式

原题要求训练前锁定四项评测。开发模式不能替代正式模式，也不能用评测反馈
选模型。先按 docs/EVALUATION.md 确认指定版本、完整任务ID、镜像、Agent、官方
runner，填写 benchmarks/manifest.json。

```text
python run.py freeze
python run.py prepare --config configs/data_formal.yaml
```

正式训练使用独立目录：
```text
python run.py sft --config configs/sft_formal.yaml --gpu 0
python run.py stage2 --config configs/stage2_formal.yaml --gpu 0
```
formal仍严格校验冻结协议，不把旧开发checkpoint自动当成正式实验。
训练前按固定协议测Base；冻结权重后再测两个训练版本。

Linux/WSL2独立vLLM环境中启动正式服务：
```text
python run.py --current-python vllm --model-dir assets/exports/base --tp 1
```

--current-python明确使用当前解释器，避免入口自动选到训练环境的.venv。
需要安装官方vLLM，模型卡建议>=0.19.0，锁定实际安装版本。
原生Windows vllm命令会明确提示系统限制；本地文本调试可使用serve。
不要将vLLM混装到训练环境而改变训练torch。

另一终端在官方runner接入后运行：
```text
python run.py evaluate --variant base
```
依次切换sft/stage2本地导出服务，再运行 --variant sft/--variant stage2。
四项完整结果产生后：
```text
python run.py summarize
```

四套官方框架未内置，指定版本和normalized.jsonl映射仍需接入。
Windows可操作Linux服务；官方Agent和容器执行仍受各框架系统限制。
不会仅凭通用启动器声称完成官方评测。

## 文件结构
- setup_env.py：两系统安装；run.py：统一入口与虚拟环境选择。
- src/qwen_swesmith/portable.py：跨平台子命令、CUDA选择、Python日志。
- configs/：下载、开发数据、训练、推理，以及正式配置的继承覆盖。
- src/qwen_swesmith/：数据、模型、编码、训练、推理、导出、评测和统计。
- docs/：硬件、方法、官方评测限制、提交要求。
- SOURCE_CODE.md：各文件完整源码；tests/是可选测试，本次没有执行。

没有Bash启动脚本。源码项目不包含已训练checkpoint、正式成绩或虚构报告。

````

## benchmarks/manifest.json

````json
{
  "frozen": false,
  "excluded_repositories": [],
  "public_prompt_files": [],
  "benchmarks": {
    "swe_pro_v2_hard": {"source_url": "UNCONFIRMED: obtain designated v2-hard", "revision": "UNCONFIRMED", "split": "v2-hard", "main_metric": "resolved_rate", "task_ids_file": "benchmarks/swe_pro_ids.json", "evaluator_commit": "UNCONFIRMED", "agent_config_file": "benchmarks/swe_agent.json", "container_digest": "UNCONFIRMED", "command": [], "seeds": [42]},
    "terminal_bench_2": {"source_url": "https://github.com/harbor-framework/terminal-bench", "revision": "UNCONFIRMED", "split": "2.0-full", "main_metric": "success_rate", "task_ids_file": "benchmarks/terminal_ids.json", "evaluator_commit": "UNCONFIRMED", "agent_config_file": "benchmarks/terminal_agent.json", "container_digest": "UNCONFIRMED", "command": [], "seeds": [42, 43, 44, 45, 46]},
    "hle": {"source_url": "https://github.com/centerforaisafety/hle", "revision": "UNCONFIRMED", "split": "UNCONFIRMED", "main_metric": "accuracy", "task_ids_file": "benchmarks/hle_ids.json", "evaluator_commit": "UNCONFIRMED", "agent_config_file": "benchmarks/hle_agent.json", "container_digest": "UNCONFIRMED", "command": [], "seeds": [42]},
    "asi_bench": {"source_url": "https://github.com/apexin-ai/ASI-Bench", "revision": "UNCONFIRMED", "split": "UNCONFIRMED", "main_metric": "UNCONFIRMED", "task_ids_file": "benchmarks/asi_ids.json", "evaluator_commit": "UNCONFIRMED", "agent_config_file": "benchmarks/asi_agent.json", "container_digest": "UNCONFIRMED", "command": [], "seeds": [42]}
  }
}

````

## configs/data.yaml

````yaml
tasks_dir: assets/datasets/SWE-smith
experiment_mode: development
exclusion_policy: data/exclusion_policy.json
trajectories_dir: assets/datasets/SWE-smith-trajectories
trajectory_split: tool
licenses: data/licenses.json
allowed_licenses: [MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0]
benchmark_manifest: benchmarks/manifest.json
output_dir: data/processed
seed: 42
validation_fraction: 0.15
max_sft_trajectories: 3000
max_trajectories_per_task: 2
max_dpo_pairs: 1000
max_pairs_per_task: 1
near_duplicate_hamming: 3
min_problem_chars: 80
max_message_chars: 2000000
failure_patterns: ['out of memory', 'docker daemon', 'connection refused', 'no space left on device', 'rate limit exceeded']

````

## configs/data_formal.yaml

````yaml
_base: configs/data.yaml
experiment_mode: formal
output_dir: data/processed_formal

````

## configs/download.yaml

````yaml
model:
  repo_id: Qwen/Qwen3.6-35B-A3B
  revision: 995ad96eacd98c81ed38be0c5b274b04031597b0
  local_dir: assets/models/Qwen3.6-35B-A3B
datasets:
  - repo_id: SWE-bench/SWE-smith
    repo_type: dataset
    revision: ea6d7173829c7ec8fa16c22055699ff2e9188091
    local_dir: assets/datasets/SWE-smith
  - repo_id: SWE-bench/SWE-smith-trajectories
    repo_type: dataset
    revision: 08e109b4a59eaeebf80e4675cd125d42e7ac99a4
    local_dir: assets/datasets/SWE-smith-trajectories

````

## configs/inference.yaml

````yaml
base_dir: assets/models/Qwen3.6-35B-A3B
quantization: bf16
reserve_gib: 8
verify_full_hash: false
attention_backend: sdpa
thinking: true
preserve_thinking: true
max_length: 8192
max_tokens: 1024
temperature: 1.0
top_p: 0.95
top_k: 20
seed: 42
host: 127.0.0.1
port: 8000

````

## configs/sft_80gb.yaml

````yaml
stage: sft
experiment_mode: development
exclusion_policy: data/exclusion_policy.json
base_dir: assets/models/Qwen3.6-35B-A3B
quantization: bf16
reserve_gib: 8
attention_backend: sdpa
verify_full_hash: true
benchmark_manifest: benchmarks/manifest.json
data_provenance: data/processed/provenance.json
train_file: data/processed/sft_train.jsonl
val_file: data/processed/sft_val.jsonl
output_dir: outputs/sft
seed: 42
thinking: true
preserve_thinking: true
max_length: 2048
window_overlap: 512
lora: {rank: 8, alpha: 16}
learning_rate: 0.0001
weight_decay: 0.01
gradient_accumulation: 16
max_steps: 500
warmup_steps: 25
eval_every: 50
save_every: 100
max_val_examples: 0
max_grad_norm: 1.0
gpu_hourly_usd: 0.0

````

## configs/sft_formal.yaml

````yaml
_base: configs/sft_80gb.yaml
experiment_mode: formal
data_provenance: data/processed_formal/provenance.json
train_file: data/processed_formal/sft_train.jsonl
val_file: data/processed_formal/sft_val.jsonl
output_dir: outputs/sft_formal

````

## configs/stage2_80gb.yaml

````yaml
stage: dpo
experiment_mode: development
exclusion_policy: data/exclusion_policy.json
base_dir: assets/models/Qwen3.6-35B-A3B
initial_adapter: outputs/sft/best_adapter
quantization: bf16
reserve_gib: 8
attention_backend: sdpa
verify_full_hash: true
benchmark_manifest: benchmarks/manifest.json
data_provenance: data/processed/provenance.json
train_file: data/processed/dpo_train.jsonl
val_file: data/processed/dpo_val.jsonl
output_dir: outputs/stage2
seed: 42
thinking: true
preserve_thinking: true
max_length: 2048
window_overlap: 512
learning_rate: 0.000005
weight_decay: 0.0
gradient_accumulation: 16
max_steps: 150
warmup_steps: 10
eval_every: 25
save_every: 50
max_val_examples: 0
max_grad_norm: 1.0
beta: 0.1
gpu_hourly_usd: 0.0

````

## configs/stage2_formal.yaml

````yaml
_base: configs/stage2_80gb.yaml
experiment_mode: formal
initial_adapter: outputs/sft_formal/best_adapter
data_provenance: data/processed_formal/provenance.json
train_file: data/processed_formal/dpo_train.jsonl
val_file: data/processed_formal/dpo_val.jsonl
output_dir: outputs/stage2_formal

````

## constraints_torch.txt

````text
# Installed separately by setup_env.py for both Windows and Linux.
torch==2.8.0
torchvision==0.23.0

````

## data/README.md

````markdown
Raw snapshots are downloaded to assets/datasets. Never modify them.
Run `python run.py licenses --config configs/data.yaml` to create a conservative license
inventory. Review the license at the historical source revision; a current
GitHub license response is only metadata evidence. Unknown licenses are excluded.

`python run.py prepare` writes sft_train.jsonl, sft_val.jsonl, dpo_train.jsonl,
dpo_val.jsonl, audit.jsonl, task_index.jsonl, stats.json and provenance.json.
The public `resolved` flag is upstream outcome evidence, not independent replay.
No scripts claim the downloaded trajectories were re-executed locally.

Default configs are explicitly DEVELOPMENT mode, using exclusion_policy.json.
Formal configs require the frozen four-benchmark manifest before data preparation.

````

## data/exclusion_policy.json

````json
{
  "note": "Development-only starting policy. Populate benchmark repository/task/prompt exclusions before formal data preparation and training.",
  "excluded_repositories": [],
  "excluded_task_ids_files": [],
  "public_prompt_files": []
}

````

## docs/EVALUATION.md

````markdown
# 四项评测接入与冻结

本项目提供官方评测进程编排、逐任务结果校验、统计和失败分析入口。
它不内置四套官方 Agent/harness，也不以自写判分器替换官方流程。
需要安装对应官方框架、下载完整任务和容器，再配置 manifest 的 command。
当前 UNCONFIRMED 项是真实待确认状态，不是可直接产生正式成绩的配置。

## 训练前必须确认
1. 指定 SWE-bench Pro v2-hard 完整快照、hard 依据和镜像；不是一般 SWE-bench
   Verified，也不是模型卡内部修订集。没有该版本则按原题联系面试方。
2. Terminal-Bench 2.0 完整任务，Harbor/Terminus-2 的具体 commit 与镜像。
3. HLE 固定版本/split、text-only 或图像题、工具、答案抽取和 judge 版本。
4. ASI-Bench 官方模式、seed、主指标和聚合方式。当前官方 README 区分
   seed31415 本地非官方评分与 seed42 私有参考官方提交；不能混称。
   seed42 官方模式还要求 OS/Docker provenance 和支持的 Agent adapter，
   不能把任意 linux_ns 自写 agent 的分数冒充官方分数。

每个 benchmark 保存完整 IDs JSON 数组、agent_config JSON、source_url、版本
SHA、evaluator_commit、容器 digest、command argv 数组和 seeds。
agent_config 至少包含 thinking、preserve_thinking、quantization、context_length、
temperature、top_p、max_tokens、tools、prompt_sha256；HLE 还需图像/抽取/judge 字段。
Terminal-Bench 的 3h/32CPU/48GB/五种子/256K/80K 及采样参数由代码强制校验。
如果任务使用多个镜像，应额外保存 task->image digest 清单并将其加入快照。

manifest.excluded_repositories 填入四项任务涉及的源仓库和 fork 家族。
public_prompt_files 只可包含获准用于排重的公开 prompt JSONL，不得下载隐藏答案。
字段填写完成后 `python run.py freeze`。formal 模式的训练/数据处理会校验冻结文件和其资产 hash。开发模式不作为正式实验。

## 外部官方 runner 的契约
command 是 argv list，可使用以下占位符：
{endpoint} {variant} {seed} {output_dir} {agent_config}。
例如 `["python", "/absolute/path/to/pinned_runner.py", "--endpoint", "{endpoint}",
"--seed", "{seed}", "--output", "{output_dir}", "--config", "{agent_config}"]`。
这是命令契约示例，不是假装存在的官方命令。
runner 负责调用被冻结版本的官方框架，并将其正式逐任务结果映射到下面字段。
三个版本共用同一个 runner 和 agent_config，只改变 model server 权重。
保留官方原始输出、完整 prompt、工具轨迹、评测日志和评分凭据。

每次 runner 成功退出后，必须在 output_dir 写 normalized.jsonl：
```json
{"task_id":"official-id","seed":42,"score":0.0,"status":"ok","seconds":123.4,"cost_usd":0.05,"raw_evidence":"/absolute/path/official-result.json"}
```
score 是该任务的官方数值按已冻结规则转换到 [0,1]，不是自行判定“看起来正确”。
resolved/pass 使用 0/1；连续指标按官方量纲转换，主指标和聚合必须确认适合此
逐任务等权汇总。如果官方主指标不是逐任务等权平均，不能直接使用本汇总器。
运行失败 status 使用 environment_error/tool_error/timeout/scorer_error，score
可为 null。未知费用允许 null；不能把没有定价当成免费。seconds 必须有记录。
raw_evidence 文件必须存在。每个完整 task ID 一行，不允许漏任务或重复任务。

统计脚本对未评分任务给出保守计零口径并单列失败，且标记此口径不是官方
排除失败的聚合成绩。应并列保留官方主指标；有未评分任务不能称正式评测完成。
对于官方统计拒绝无效评分的版本，先解决或披露 invalid，不能悄悄改成成功。
Terminal-Bench 对任务进行跨五种子的 cluster bootstrap，报告五次均值和标准差；
宏平均是四项百分制指标等权平均。置信区间条件于固定种子，重复运行波动另列。

## 部署
python run.py serve 是短上下文、text-only、一次一个请求的调试服务；不能以其 8192 token
配置声称完成原题 256K Terminal-Bench。它不执行工具，工具由官方 Agent 执行。
正式评测建议将三个模型都用 python run.py export 导出为 BF16，然后在同一独立 vLLM
环境中运行 python run.py --current-python vllm --model-dir /absolute/local/export。支持视觉的服务供包含图像的 HLE 使用。
vLLM 官方模型卡建议 >=0.19.0，但要锁定真正安装并验证的版本及 CUDA 依赖。
训练 venv 和 vLLM venv 分开，避免引擎的 torch 依赖改变训练环境。

## 失败分析
summary 生成 failure_review.jsonl，至少人工审阅 20 个案例。
类别：localization_error / patch_error / test_understanding_error /
environment_or_tool_error / timeout / other。填写 explanation 和证据路径。
建议后续实验：加入验证过的 repo 上下文偏好；重放偏好标签；比较窗口长度与
保留完整 system/issue 的策略。最后用真实成绩编写不超过一页的 report.pdf。

官方资料（2026-10-02）：
- https://github.com/apexin-ai/ASI-Bench
- https://github.com/centerforaisafety/hle
- https://github.com/harbor-framework/harbor
- https://github.com/harbor-framework/terminal-bench
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B

## Windows / Linux Python入口（2026-10-03）

下载、数据处理、SFT、DPO、本地文本服务和CPU导出共用run.py。
官方vLLM CUDA后端和多项评测容器依赖Linux，不能宣称全部原生Windows兼容。
Windows可使用本项目serve调试，正式框架在WSL2/Linux服务器中运行。

````

## docs/HARDWARE.md

````markdown
# 显存结论与硬件选择

本项目不保证指定模型在单卡 24GB 上训练，也没有用更小模型偷偷替代。
交付的可靠路线是 BF16 基座 + 仅语言注意力层 LoRA；基础专家和视觉编码器冻结。

## 为什么 24GB 不够

1. 原模型约 35B 总参数。BF16 理论权重约 70GB（65.2GiB），不是 3B × 2。
2. 理想的全部 4-bit 权重下界约 17.5GB（16.3GiB），还没有量化元数据、
   未量化模块、激活、梯度、LoRA 优化器、logits、临时缓冲区和 CUDA 开销。
3. 本次核查的 Transformers `Qwen3_5MoeExperts` 将专家矩阵保存为 3D
   `nn.Parameter`，不是普通 `nn.Linear`。不能因为设置了
   `BitsAndBytesConfig(load_in_4bit=True)` 就断言所有专家已量化。
   配置计算的路由专家本身有约 32.21B 参数，BF16 约 60GiB。
   本项目不包含未经 GPU 验证的专家替换/量化补丁，因此直接拒绝 NF4 配置。
4. Terminal-Bench 指定 262144 上下文。按 10 个全注意力层、2 个 KV head、
   head_dim=256、BF16 粗算，batch=1 的 KV cache 约 5GiB。
   这是混合线性注意力架构，不能按 40 个全注意力层夸大 KV；线性状态和其他
   开销也不能忽略。推理引擎的实际布局可能不同。

## 选择建议（容量判断，未做实机性能保证）

| 设备 | 本项目路线 |
|---|---|
| 24GB RTX 3090/4090 等 | 可做数据处理和 CPU 单元测试；BF16 训练不能运行 |
| 48GB GPU | BF16 全部权重仍装不下，不能解决此后端的问题 |
| A100/H100 80GB | 可作为短上下文、batch=1、rank=8 的 LoRA 候选；仍需 preflight 和实际 OOM 验证 |
| H100 NVL 94GB | 比 80GB 留出更多余量，需验证具体服务/训练栈 |
| H200 141GB | 本方案更适合的选择；能给更长训练上下文和推理缓冲留余量 |
| 多卡服务器 | 官方 vLLM TP 推理可配置；此训练器不实现多卡训练，不能把多卡显存简单相加 |

如果仅有 24GB，另一条可能路线是专用、已验证的 MoE 量化/CPU offload 后端。
它不是本项目已经验证的功能；CPU offload 推理也不能替代 SFT 训练。
要保留原题指定模型，不应直接换成 7B/14B。

80GB 的预设是 2048 token 窗口，不是原题正式评测的 256K 配置。
在 H200 上可将训练配置 max_length 调到 4096/8192，减少长轨迹窗口损失和
DPO 长补丁排除，但要在开发集选择后冻结并保存新的 config。

主机内存建议至少 128GB，CPU 合并导出最好 192GB 或以上。
下载原模型、数据、三个完整导出和临时缓存时建议预留约 400GB 磁盘空间；
这是容量规划估计，不是实测需求。完整原模型权重不包含在交付 ZIP 中。

资料（访问于 2026-10-02）：
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/main/config.json
- https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py
- https://github.com/bitsandbytes-foundation/bitsandbytes/issues/1849
- https://www.nvidia.com/en-us/data-center/h100/
- https://www.nvidia.com/en-us/data-center/h200/

````

## docs/METHOD.md

````markdown
# 实验方法与边界

## 数据
固定 SWE-smith tasks 与 trajectories 两个公开快照，使用 tool split。
开发模式按 data/exclusion_policy.json 排除，默认空清单不保证无评测泄漏。
正式模式使用先冻结的四项 benchmark 协议，保存两种模式标记和独立输出目录。
实际 messages 是 JSON 字符串，content 可能是 text block 列表，工具响应使用
tool_call_ids。本项目统一为 Qwen 支持的标准工具消息，使用原版 chat template。
通过 instance_id 与任务表关联，未知/不允许许可证排除。
按配置的仓库、任务 ID、公开 prompt 近似排重；同一仓库全部进同一 split。
SimHash 只是一种近似排重，不保证发现语义改写、跨 fork 复制或未知评测题。
基座预训练阶段是否已经看过评测题也不是此次排重能证明的。

数据集 MIT 标记不能替代源仓库代码许可。GitHub 当前许可清单也不是历史版本
许可证明；需要保留历史来源和归属声明。未知许可默认不训练。

resolved 来自上游记录。代码没有伪称已独立重放全部容器；建议正式实验对抽样
轨迹重放，记录噪声率及环境错误，并人工核对问题与实际补丁是否对应。
难度标签是成功/失败数量比例的代理指标，不是官方难度或真实解题复杂度。

## SFT
仅成功轨迹训练。仅 assistant 内容、工具调用和结束标记计入监督；用户和工具
输出 mask 为 -100。用完整渲染后的字符 offset 对齐，避免 Qwen 历史 thinking
保留规则导致 prefix token 长度不一致。SFT 使用重叠 token 窗口，每个目标只
监督一次；较晚窗口可能不包含原始 system 和 issue，这是节省显存的限制。
不将其称为完整长上下文轨迹训练。micro batch=1，gradient accumulation=16。

只训练 full-attention 和 DeltaNet 的语言投影：q/k/v/o_proj、in_proj_qkv、
in_proj_z、in_proj_a、in_proj_b、out_proj（实际命中的全名保存到日志）。
专家、router、共享专家、视觉模块、embedding、lm_head 冻结。
这不是 all-linear，也没有添加所有 256 个专家的 adapter。

## 第二阶段：补丁偏好 DPO
在同一 task 的上游成功/失败轨迹之间选不同的最终补丁。
prompt 只用两条轨迹共享的初始 system/user 指令，加统一的补丁输出要求；
不使用分歧后工具输出、参考修复或 benchmark 测试。
chosen/rejected 为两份完整 unified diff，超长 pair 排除并留日志。
这是一种 issue-to-patch 偏好辅助任务，不是对完整 Agent 轨迹做在线 RL。
没有仓库上下文时难以充分判断补丁，是这个轻量目标的明确偏差。
工具任务 SFT 与 patch-only DPO 存在格式差异，可能牺牲工具使用能力。

正样本标签 resolved=True，负样本 resolved=False 且有合法非空补丁。
最后若干消息含常见环境失败关键词的负样本排除；这不是完美的环境归因，
仍需审查失败样本。更严格的下一步是用训练任务官方 harness 重放并清除错误标签。

目标：
L = -log sigmoid(beta * [(log pi(y+|x)-log pi(y-|x))
                         -(log ref(y+|x)-log ref(y-|x))])
logprob 是完整 assistant 补丁 token 的总和，长度差异可能造成偏好偏差。
reference 是冻结的 SFT adapter；policy 从同一个 SFT adapter 初始化。
两者共享冻结基座，保存 reference adapter 副本；不会同时复制两份 35B 权重。
先无梯度计算 DPO 系数，再分别重放 chosen/rejected 前向并反传；所有 dropout
设为 0，得到相同的梯度并降低同时保存两份激活图的开销。
这里实现了 DPO 公式，未使用 TRL，以明确控制 mask、参考模型和显存。

## 对照和停止
Base 是不训练对照，SFT 与 stage2 保持推理协议一致。
预设固定最大步数，并按独立 DEV loss 选 best_adapter；DEV 不回流训练。
阶段二 DPO loss 最小并不保证任务成功率最高，后续可增加训练任务的独立执行
开发集作为选择指标；不能改用四项评测反馈选 checkpoint。
无 optimizer-resume 功能：中断的运行有失败资源日志，需用新的 output_dir 重跑，
不能宣称无缝恢复了原随机采样序列。

````

## docs/SUBMISSION.md

````markdown
# 最终交付清单

- 个人私有 GitHub repo：完整代码、固定配置、安装命令、依赖锁、数据来源/许可。
- 两个公开 Hugging Face 模型：SFT 与 stage2 adapter，公开可下载，保存 revision。
- HF 模型 README：官方基座 revision、本地加载命令、训练方法、许可证、限制。
- logs：stdout、metrics、错误/超时、资源、GPU 小时、费用依据、主动工作时间。
- curves：独立训练/验证 loss 图；DPO chosen/rejected reward 和偏好准确率图；源 CSV。
- results：四项 × 三版本完整逐任务结果；Terminal-Bench 五次的原始结果。
- analysis：配对 bootstrap、失败率、成本、20+ 人工失败案例、三个后续实验。
- report.pdf：一页，摘要 150–200 中文字符，过程，结果。没有真实成绩前不要填数字。

注意：此源码项目不包含已训练 checkpoint、正式报告或完整评测成绩。
本次跨平台修改按用户要求没有运行验证，也无 Windows/Linux GPU 运行证明。
默认开发模式训练不自动满足原题要求；正式实验使用 formal 配置和冻结评测协议。

````

## models/README.md

````markdown
All base weights, tokenizer and processor files must be downloaded before
training. All training/inference `from_pretrained` calls use validated LOCAL
paths and `local_files_only=True`, with Hub offline variables enabled.

SFT output: outputs/sft/final_adapter (or best_adapter selected on DEV).
Stage2 output: outputs/stage2/final_adapter. It contains the FULL updated
adapter inherited from SFT, not just a delta that needs another adapter.
The unchanged official base snapshot is still needed to load either adapter.

No checkpoints have been trained or uploaded with this source deliverable.

````

## pyproject.toml

````toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "qwen-swesmith-local"
version = "0.1.0"
description = "Local-only Qwen3.6 MoE LoRA SFT and patch preference DPO"
requires-python = ">=3.12"
dependencies = ["PyYAML>=6", "numpy>=2", "psutil>=6"]

[project.scripts]
qs = "qwen_swesmith.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

````

## requirements.txt

````text
# Exact direct pins verified against PyPI metadata on 2026-10-02.
# Native Windows / Linux shared dependencies. Install torch/torchvision first
# through setup_env.py, which selects explicit official CUDA wheels.
# This is NOT a full transitive lock; each real run records pip freeze.
transformers==5.18.0
peft==0.21.2
accelerate==1.15.0
datasets==5.0.1
huggingface-hub==1.33.0
tokenizers==0.23.2
safetensors==0.8.0
PyYAML==6.0.3
numpy==2.5.3
matplotlib==3.11.2
psutil==7.2.2
fastapi==0.142.2
uvicorn==0.54.0
pydantic==2.13.5
Jinja2==3.1.6
pillow==12.3.0

````

## run.py

````python
"""One Python entry point for native Windows and Linux. No Bash required."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    use_current = "--current-python" in sys.argv[1:]
    if use_current:
        sys.argv.remove("--current-python")
    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not use_current and venv_python.is_file() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        raise SystemExit(subprocess.call([str(venv_python), "-u", str(Path(__file__).resolve()), *sys.argv[1:]], env=env))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ROOT / "src"))
    from qwen_swesmith.portable import main as launch
    launch()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileNotFoundError, ModuleNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)

````

## scripts/download.sh

````bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
qs download --config configs/download.yaml
qs licenses --config configs/data.yaml

````

## scripts/evaluate_all.sh

````bash
#!/usr/bin/env bash
# Start the corresponding model server BEFORE calling this script.
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT="${1:?Usage: evaluate_all.sh base|sft|stage2}"
case "$VARIANT" in base|sft|stage2) ;; *) exit 2 ;; esac
for BENCHMARK in swe_pro_v2_hard terminal_bench_2 hle asi_bench; do
  qs evaluate --benchmark "$BENCHMARK" --variant "$VARIANT"
done

````

## scripts/serve_vllm.sh

````bash
#!/usr/bin/env bash
# Use an ISOLATED evaluation environment, not the training venv.
# Export all three variants through qs export first. No remote model identifiers.
set -euo pipefail
if [ "$#" -lt 1 ]; then
  echo 'Usage: bash scripts/serve_vllm.sh /absolute/local/export [tensor_parallel_size]'
  exit 2
fi
MODEL_DIR="$(realpath "$1")"
TP_SIZE="${2:-1}"
test -f "$MODEL_DIR/config.json"
test -f "$MODEL_DIR/export_provenance.json"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
vllm serve "$MODEL_DIR" \
  --served-model-name local-qwen \
  --dtype bfloat16 \
  --tensor-parallel-size "$TP_SIZE" \
  --max-model-len 262144 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.90 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --host 127.0.0.1 --port 8000

````

## scripts/train.sh

````bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True
mkdir -p outputs/console
qs preflight --config configs/sft_80gb.yaml --inspect
qs prepare --config configs/data.yaml
qs train --config configs/sft_80gb.yaml 2>&1 | tee outputs/console/sft.log
qs curves --run-dir outputs/sft
qs train --config configs/stage2_80gb.yaml 2>&1 | tee outputs/console/stage2.log
qs curves --run-dir outputs/stage2

````

## setup_env.py

````python
"""Create a local venv and install explicit CUDA wheels on Windows or Linux.

Usage: python setup_env.py --cuda cu128
This installs dependencies; it does not download models or execute tests.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description="Install the same project on Windows and Linux")
    p.add_argument("--cuda", choices=["cu126", "cu128", "cu129", "cpu"], default="cu128")
    args = p.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Please run this installer with Python 3.12 (Windows: py -3.12 setup_env.py).")
    envdir = ROOT / ".venv"
    python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(envdir)
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    commands = [
        [str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        [str(python), "-m", "pip", "install", "torch==2.8.0", "torchvision==0.23.0",
         "--index-url", f"https://download.pytorch.org/whl/{args.cuda}"],
        [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"),
         "-c", str(ROOT / "constraints_torch.txt")],
        [str(python), "-m", "pip", "install", "-e", str(ROOT), "--no-deps"],
    ]
    for command in commands:
        print("Installing:", subprocess.list2cmdline(command), flush=True)
        subprocess.run(command, cwd=ROOT, env=environment, check=True)
    frozen = subprocess.check_output([str(python), "-m", "pip", "freeze"], env=environment, text=True, encoding="utf-8")
    (ROOT / "dependencies.lock.txt").write_text(frozen, encoding="utf-8")
    (ROOT / "installation.json").write_text(json.dumps({"python": str(python), "platform": sys.platform,
        "torch": "2.8.0", "torchvision": "0.23.0", "wheel_index": args.cuda}, indent=2), encoding="utf-8")
    print("Installation complete. Next: python run.py download", flush=True)
    if args.cuda == "cpu":
        print("CPU installation is for download/data preparation only; model training needs a sufficiently large CUDA GPU.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Installation failed (exit {e.returncode}). Fix the error above and rerun this installer.")

````

## src/qwen_swesmith/__init__.py

````python
"""Reproducible, local-only SWE-smith post-training project."""
__version__ = "0.1.0"

````

## src/qwen_swesmith/analysis.py

````python
from __future__ import annotations
from collections import defaultdict
import csv
import json
from .common import path, rows, read_json, write_json, write_rows
from .benchmarks import locked, validate_results, NAMES


def paired_bootstrap(base, final, repeats=10000, seed=42):
    import numpy as np
    a, b = np.asarray(base, dtype=float), np.asarray(final, dtype=float)
    if a.shape != b.shape or a.ndim != 1 or not len(a):
        raise ValueError("Paired samples must be nonempty vectors of the same shape")
    rng = np.random.default_rng(seed)
    delta = b - a
    draws = []
    for _ in range(repeats):
        draws.append(float(delta[rng.integers(0, len(a), size=len(a))].mean() * 100))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"delta_percentage_points": float(delta.mean() * 100),
            "ci95_percentage_points": [float(lo), float(hi)]}, draws


def summarize(manifest_file):
    import numpy as np
    manifest = locked(manifest_file)
    result = {"benchmarks": {}, "manifest_sha256": manifest["lock_sha256"],
              "failure_policy": "All fixed task IDs retained; unscored failures counted as 0 in conservative macro, and separately reported."}
    table = []
    macro_draws = {"sft": [], "stage2": []}
    for benchmark_index, name in enumerate(NAMES):
        b = manifest["benchmarks"][name]
        ids = read_json(b["task_ids_file"])
        by_variant = {}
        for variant in ("base", "sft", "stage2"):
            all_rows = []
            scores = []
            vectors = []
            for seed in b["seeds"]:
                record = list(rows(f"outputs/results/{variant}/{name}/seed_{seed}/normalized.jsonl"))
                validate_results(record, ids, seed)
                indexed = {r["task_id"]: r for r in record}
                vector = np.array([indexed[i]["score"] if indexed[i]["score"] is not None else 0.0 for i in ids])
                vectors.append(vector)
                scores.append(float(vector.mean() * 100))
                all_rows.extend(record)
            priced = [r for r in all_rows if r["cost_usd"] is not None]
            score_stats, _ = paired_bootstrap(np.zeros(len(ids)), np.mean(vectors, axis=0), seed=42 + benchmark_index)
            item = {"score_percent": float(np.mean(scores)),
                    "score_ci95_percent": score_stats["ci95_percentage_points"],
                    "repeat_std_percent": float(np.std(scores, ddof=1)) if len(scores) > 1 else None,
                    "failure_rate_percent": sum(r["status"] != "ok" for r in all_rows) / len(all_rows) * 100,
                    "mean_seconds": sum(r["seconds"] for r in all_rows) / len(all_rows),
                    "total_cost_usd": sum(r["cost_usd"] for r in priced) if len(priced) == len(all_rows) else None,
                    "known_cost_usd": sum(r["cost_usd"] for r in priced),
                    "unpriced_tasks": len(all_rows) - len(priced),
                    "mean_cost_usd": sum(r["cost_usd"] for r in priced) / len(all_rows) if len(priced) == len(all_rows) else None,
                    "status_counts": {s: sum(r["status"] == s for r in all_rows)
                                      for s in sorted({r["status"] for r in all_rows})},
                    "has_unscored_failures": any(r["score"] is None for r in all_rows)}
            by_variant[variant] = (item, np.mean(vectors, axis=0))
            table.append({"benchmark": name, "variant": variant, **{k: v for k, v in item.items() if k != "status_counts"}})
        output = {v: item for v, (item, _) in by_variant.items()}
        for variant in ("sft", "stage2"):
            # Cluster tasks across repeated seeds; same task is not counted five independent times.
            stats, draws = paired_bootstrap(by_variant["base"][1], by_variant[variant][1], seed=42 + benchmark_index)
            output[variant]["vs_base"] = stats
            macro_draws[variant].append(draws)
        output["stage2"]["vs_sft"], _ = paired_bootstrap(by_variant["sft"][1], by_variant["stage2"][1])
        result["benchmarks"][name] = output
    result["macro"] = {v: float(np.mean([result["benchmarks"][n][v]["score_percent"] for n in NAMES]))
                       for v in ("base", "sft", "stage2")}
    result["macro_improvement"] = {}
    for v, draws in macro_draws.items():
        macro = np.mean(np.asarray(draws), axis=0)
        result["macro_improvement"][v] = {"delta_percentage_points": result["macro"][v] - result["macro"]["base"],
           "ci95_percentage_points": [float(x) for x in np.quantile(macro, [0.025, 0.975])],
           "ci_note": "Task bootstrap conditional on the fixed seeds; repeat variability reported separately"}
    write_json("outputs/analysis/summary.json", result)
    p = path("outputs/analysis/summary.csv")
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    failures = []
    for n in NAMES:
        for seed in manifest["benchmarks"][n]["seeds"]:
            for r in rows(f"outputs/results/stage2/{n}/seed_{seed}/normalized.jsonl"):
                if r["score"] is None or r["score"] < 1:
                    failures.append({"benchmark": n, **r, "error_category": "UNREVIEWED", "explanation": ""})
    write_rows("outputs/analysis/failure_review.jsonl", failures)
    print(json.dumps(result["macro_improvement"], indent=2))


def curves(run_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    run = path(run_dir)
    records = list(rows(run / "metrics.jsonl"))
    metrics = sorted({k for r in records for k in ("loss", "chosen_reward", "rejected_reward", "preference_accuracy", "lr") if k in r})
    out = run / "curves"; out.mkdir(exist_ok=True)
    with (out / "source.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["step", "split", *metrics]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(records)
    for metric in metrics:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for split in ("train", "val"):
            data = [r for r in records if r["split"] == split and metric in r]
            if data:
                ax.plot([r["step"] for r in data], [r[metric] for r in data], label=split, linewidth=1.3)
        ax.set(xlabel="Optimizer step", ylabel=metric, title=f"{run.name}: {metric}")
        ax.grid(alpha=0.2); ax.legend()
        for r in records:
            if r.get("checkpoint") and r["step"]:
                ax.axvline(r["step"], color="gray", alpha=0.15, linewidth=0.7)
        fig.tight_layout(); fig.savefig(out / f"{metric}.png", dpi=300); fig.savefig(out / f"{metric}.pdf")
        plt.close(fig)

````

## src/qwen_swesmith/benchmarks.py

````python
"""Version lock and official-run orchestration. No substitute benchmark scorers."""
from __future__ import annotations
import json
import math
import os
import subprocess
import time
from pathlib import Path
from .common import path, read_json, write_json, rows, digest, file_hash

NAMES = ("swe_pro_v2_hard", "terminal_bench_2", "hle", "asi_bench")


def training_protocol(cfg):
    """Formal runs keep the original pre-training lock; development is explicit."""
    mode = cfg.get("experiment_mode", "formal")
    if mode == "formal":
        return locked(cfg["benchmark_manifest"])
    if mode != "development":
        raise ValueError("experiment_mode must be development or formal")
    policy_path = cfg["exclusion_policy"]
    policy = read_json(policy_path)
    for key in ("excluded_repositories", "excluded_task_ids_files", "public_prompt_files"):
        if not isinstance(policy.get(key), list):
            raise ValueError(f"Development exclusion policy missing {key}")
    print("[DEVELOPMENT MODE] Benchmark protocol not locked. This run is not a completed take-home experiment.", flush=True)
    result = {"experiment_mode": mode, "excluded_repositories": policy["excluded_repositories"],
              "public_prompt_files": policy["public_prompt_files"],
              "benchmarks": {str(i): {"task_ids_file": p} for i, p in enumerate(policy["excluded_task_ids_files"])}}
    assets = {p: file_hash(path(p)) for p in [policy_path, *policy["excluded_task_ids_files"], *policy["public_prompt_files"]]}
    result["lock_sha256"] = "development:" + digest({"policy": result, "assets": assets})
    return result


def validate_manifest(m, verify_files=True):
    if set(m.get("benchmarks", {})) != set(NAMES):
        raise ValueError("Manifest must contain exactly the four specified benchmarks")
    for name, b in m["benchmarks"].items():
        for key in ("source_url", "revision", "split", "main_metric", "task_ids_file",
                    "evaluator_commit", "agent_config_file", "container_digest", "command", "seeds"):
            if not b.get(key) or "UNCONFIRMED" in str(b[key]):
                raise ValueError(f"{name}.{key} must be confirmed BEFORE training")
        if len(b["evaluator_commit"]) != 40 or len(b["revision"]) != 40:
            raise ValueError(f"{name}: revisions must be full immutable commit hashes")
        if not isinstance(b["command"], list) or not all(isinstance(x, str) for x in b["command"]):
            raise ValueError("command must be an argv list, never a shell string")
        if "sha256:" not in b["container_digest"]:
            raise ValueError(f"{name}: pin the container digest")
        if len(set(b["seeds"])) != len(b["seeds"]):
            raise ValueError("Duplicate evaluation seeds")
        if name == "terminal_bench_2" and len(b["seeds"]) != 5:
            raise ValueError("Terminal-Bench requires five seeds")
        if verify_files:
            ids = read_json(b["task_ids_file"])
            if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
                raise ValueError(f"{name}: invalid full task ID list")
            agent = read_json(b["agent_config_file"])
            for k in ("thinking", "preserve_thinking", "quantization", "context_length",
                      "temperature", "top_p", "max_tokens", "tools", "prompt_sha256"):
                if k not in agent:
                    raise ValueError(f"{name}: missing inference setting {k}")
            if name == "terminal_bench_2":
                required = {"timeout_seconds": 10800, "cpus": 32, "ram_gb": 48,
                            "temperature": 1.0, "top_p": 0.95, "top_k": 20,
                            "max_tokens": 80000, "context_length": 262144,
                            "framework": "Harbor", "agent": "Terminus-2"}
                for k, v in required.items():
                    if agent.get(k) != v:
                        raise ValueError(f"Terminal-Bench setting {k} must be {v}")
            if name == "hle":
                for k in ("includes_images", "answer_extraction", "judge_version"):
                    if k not in agent:
                        raise ValueError(f"HLE: missing {k}")
    if not isinstance(m.get("excluded_repositories"), list):
        raise ValueError("excluded_repositories must be an explicitly reviewed list")


def freeze(filename):
    p = path(filename)
    m = read_json(p)
    validate_manifest(m)
    if m.get("frozen"):
        raise ValueError("Already frozen; verify the existing lock instead of rewriting it")
    assets = {}
    for b in m["benchmarks"].values():
        for key in ("task_ids_file", "agent_config_file"):
            assets[b[key]] = file_hash(path(b[key]))
    for extra in m.get("public_prompt_files", []):
        assets[extra] = file_hash(path(extra))
    m.update(frozen=True, asset_hashes=assets, frozen_at=time.time())
    m["lock_sha256"] = digest(m)
    write_json(p, m)


def locked(filename):
    m = read_json(filename)
    if not m.get("frozen"):
        raise ValueError("Benchmark protocol is not frozen; run qs freeze after confirmation")
    claimed = m.pop("lock_sha256")
    if digest(m) != claimed:
        raise ValueError("Frozen manifest was changed")
    m["lock_sha256"] = claimed
    validate_manifest(m)
    for p, h in m["asset_hashes"].items():
        if file_hash(path(p)) != h:
            raise ValueError(f"Frozen asset changed: {p}")
    return m


def run(filename, name, variant, endpoint):
    m = locked(filename)
    if name not in NAMES or variant not in {"base", "sft", "stage2"}:
        raise ValueError("Unknown benchmark or model version")
    # Exact official CLI/adaptor contract is pinned by operator for its version.
    # The external command MUST generate normalized.jsonl and preserve official raw logs.
    b = m["benchmarks"][name]
    for seed in b["seeds"]:
        out = path(f"outputs/results/{variant}/{name}/seed_{seed}")
        if out.exists():
            raise FileExistsError(f"Existing evaluation directory: {out}")
        out.mkdir(parents=True)
        values = {"endpoint": endpoint, "variant": variant, "seed": str(seed),
                  "output_dir": str(out), "agent_config": str(path(b["agent_config_file"]))}
        # Replace only these literals; do not interpret arbitrary braces in CLI JSON.
        cmd = list(b["command"])
        for i in range(len(cmd)):
            for key, value in values.items():
                cmd[i] = cmd[i].replace("{" + key + "}", value)
        env = os.environ.copy()
        env.update(QS_MODEL_ENDPOINT=endpoint, QS_VARIANT=variant,
                   QS_EVAL_SEED=str(seed), QS_OUTPUT_DIR=str(out))
        t = time.time()
        with (out / "process.log").open("w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, cwd=path(b.get("cwd", ".")), env=env,
                                  stdout=f, stderr=subprocess.STDOUT, check=False)
        write_json(out / "execution.json", {"argv": cmd, "seconds": time.time() - t,
                   "returncode": proc.returncode, "manifest_sha256": m["lock_sha256"]})
        if proc.returncode:
            raise RuntimeError(f"Official runner failed; see {out / 'process.log'}")
        validate_results(list(rows(out / "normalized.jsonl")), read_json(b["task_ids_file"]), seed)


def validate_results(records, ids, seed):
    if len(records) != len(ids) or {r["task_id"] for r in records} != set(ids):
        raise ValueError("Missing/extra/duplicate tasks: full evaluation required")
    for r in records:
        if r.get("seed") != seed:
            raise ValueError("Result seed mismatch")
        if r.get("status") not in {"ok", "environment_error", "tool_error", "timeout", "scorer_error"}:
            raise ValueError("Unknown result status")
        score = r.get("score")
        if score is None and r["status"] == "ok":
            raise ValueError("Successful evaluation missing official score")
        if score is not None and (isinstance(score, bool) or not 0 <= score <= 1):
            raise ValueError("Normalized score must be a number in [0,1]")
        for key in ("seconds", "cost_usd", "raw_evidence"):
            if key not in r:
                raise ValueError(f"Result missing {key}")
        if not isinstance(r["seconds"], (int, float)) or not math.isfinite(r["seconds"]) or r["seconds"] < 0:
            raise ValueError("Invalid elapsed time")
        cost = r["cost_usd"]
        if cost is not None and (not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0):
            raise ValueError("Invalid cost; use null for unpriced runs")
        if not path(r["raw_evidence"]).is_file():
            raise FileNotFoundError(r["raw_evidence"])

````

## src/qwen_swesmith/cli.py

````python
from __future__ import annotations
import argparse


def main():
    p = argparse.ArgumentParser(description="Local Qwen3.6 + SWE-smith post-training")
    sub = p.add_subparsers(dest="command", required=True)
    for name, default in (("download", "configs/download.yaml"), ("licenses", "configs/data.yaml"),
                          ("prepare", "configs/data.yaml"), ("preflight", "configs/sft_80gb.yaml"),
                          ("train", "configs/sft_80gb.yaml"), ("serve", "configs/inference.yaml")):
        q = sub.add_parser(name)
        q.add_argument("--config", default=default)
        if name == "preflight":
            q.add_argument("--inspect", action="store_true")
        if name == "serve":
            q.add_argument("--adapter")
    for name in ("freeze", "evaluate", "summarize"):
        q = sub.add_parser(name)
        q.add_argument("--manifest", default="benchmarks/manifest.json")
        if name == "evaluate":
            q.add_argument("--benchmark", required=True)
            q.add_argument("--variant", choices=["base", "sft", "stage2"], required=True)
            q.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    q = sub.add_parser("curves"); q.add_argument("--run-dir", required=True)
    q = sub.add_parser("export")
    q.add_argument("--base", default="assets/models/Qwen3.6-35B-A3B")
    q.add_argument("--adapter"); q.add_argument("--output", required=True)
    a = p.parse_args()
    if a.command == "download":
        from .download import download
        download(a.config)
    elif a.command == "licenses":
        from .download import licenses
        licenses(a.config)
    elif a.command == "prepare":
        from .data import prepare
        prepare(a.config)
    elif a.command == "preflight":
        from .preflight import preflight
        preflight(a.config, a.inspect)
    elif a.command == "train":
        from .train import train
        train(a.config)
    elif a.command == "serve":
        from .inference import serve
        serve(a.config, a.adapter)
    elif a.command == "freeze":
        from .benchmarks import freeze
        freeze(a.manifest)
    elif a.command == "evaluate":
        from .benchmarks import run
        run(a.manifest, a.benchmark, a.variant, a.endpoint)
    elif a.command == "summarize":
        from .analysis import summarize
        summarize(a.manifest)
    elif a.command == "curves":
        from .analysis import curves
        curves(a.run_dir)
    elif a.command == "export":
        from .export import export
        export(a.base, a.output, a.adapter)


if __name__ == "__main__":
    main()

````

## src/qwen_swesmith/common.py

````python
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def path(value):
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def config(filename, _seen=None):
    import yaml
    filename = path(filename)
    seen = set() if _seen is None else set(_seen)
    if filename in seen:
        raise ValueError("Cyclic _base configuration")
    seen.add(filename)
    with filename.open(encoding="utf-8") as f:
        value = yaml.safe_load(f)
    if not isinstance(value, dict):
        raise ValueError(f"Expected configuration mapping: {filename}")
    base = value.pop("_base", None)
    if base:
        parent = config(base, seen)
        def merge(a, b):
            result = dict(a)
            for key, item in b.items():
                result[key] = merge(result[key], item) if isinstance(result.get(key), dict) and isinstance(item, dict) else item
            return result
        return merge(parent, value)
    return value


def digest(value):
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(value.encode()).hexdigest()


def file_hash(filename):
    h = hashlib.sha256()
    with Path(filename).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(filename, data):
    p = path(filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def read_json(filename):
    return json.loads(path(filename).read_text(encoding="utf-8"))


def rows(filename):
    with path(filename).open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{filename}:{i}: invalid JSON") from e


def write_rows(filename, records):
    p = path(filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def offline():
    # Call BEFORE importing datasets/transformers/huggingface_hub.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["WANDB_DISABLED"] = "true"


def local_dir(value, required=()):
    p = path(value)
    if not p.is_dir():
        raise FileNotFoundError(f"Local directory missing: {p}; run qs download first")
    for name in required:
        if not (p / name).is_file():
            raise FileNotFoundError(p / name)
    return p


def seed_all(seed):
    random.seed(seed)
    import numpy as np
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def snapshot(out, cfg):
    out = path(out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "config.json").exists():
        raise FileExistsError(f"Run directory already used: {out}; choose a new output_dir")
    write_json(out / "config.json", cfg)
    write_json(out / "launch.json", {"argv": sys.argv, "python": sys.version, "time": time.time()})
    installed = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (out / "dependencies.lock.txt").write_text(installed, encoding="utf-8")
    return out

````

## src/qwen_swesmith/data.py

````python
from __future__ import annotations
from collections import Counter, defaultdict
import json
import random
import re
from .common import config, path, local_dir, offline, write_json, write_rows, read_json, digest, file_hash
from .schema import normalize, normalize_diff, simhash
from .benchmarks import training_protocol


def parquet_files(directory, split):
    root = local_dir(directory)
    files = sorted(root.rglob(f"{split}-*.parquet"))
    if not files:
        raise FileNotFoundError(f"No {split}-*.parquet found in {root}; inspect pinned snapshot")
    return files


def local_dataset(directory, split):
    offline()
    from datasets import load_dataset
    # parquet builder reads local paths only; no Hub dataset script executes.
    return load_dataset("parquet", data_files={split: [str(p) for p in parquet_files(directory, split)]}, split=split)


def load_tasks(directory):
    tasks = {}
    for row in local_dataset(directory, "train"):
        iid = row["instance_id"]
        if iid in tasks:
            raise ValueError(f"Duplicate official task ID: {iid}")
        tasks[iid] = dict(row)
    return tasks


def common_prefix(a, b):
    result = []
    for x, y in zip(a, b):
        if x != y:
            break
        result.append(x)
    # DPO is a patch completion task conditioned on initial shared instructions.
    # Never include post-divergence observations or gold patches in its prompt.
    return result


def build(records, tasks, cfg, licenses, manifest):
    from .download import original_repo
    rng = random.Random(cfg["seed"])
    audits = []
    valid = defaultdict(list)
    seen = set()
    banned = {original_repo(r) for r in manifest["excluded_repositories"]}
    benchmark_ids = set()
    for b in manifest["benchmarks"].values():
        benchmark_ids.update(read_json(b["task_ids_file"]))
    public_prompts = []
    for filename in manifest.get("public_prompt_files", []):
        from .common import rows
        public_prompts.extend(r["prompt"] for r in rows(filename))
    benchmark_hashes = [simhash(s) for s in public_prompts]
    near_buckets = defaultdict(list)
    problem_seen = {}
    for r in records:
        iid = r.get("instance_id")
        tid = r.get("traj_id")
        try:
            if iid not in tasks:
                raise ValueError("task_join_missing")
            task = tasks[iid]
            repo = original_repo(task["repo"])
            if repo in banned or iid in benchmark_ids:
                raise ValueError("benchmark_overlap")
            license_record = licenses.get(repo, {})
            if license_record.get("spdx") not in cfg["allowed_licenses"]:
                raise ValueError("unapproved_source_license")
            problem = task.get("problem_statement") or ""
            if len(problem) < cfg["min_problem_chars"]:
                raise ValueError("missing_or_short_problem")
            h = simhash(problem)
            if any((h ^ b).bit_count() <= cfg["near_duplicate_hamming"] for b in benchmark_hashes):
                raise ValueError("benchmark_prompt_near_duplicate")
            if iid not in problem_seen:
                candidates = set()
                for band in range(4):
                    candidates.update(near_buckets[(band, (h >> (16 * band)) & 0xffff)])
                if any((h ^ problem_seen[other]).bit_count() <= cfg["near_duplicate_hamming"] for other in candidates):
                    raise ValueError("duplicate_task_problem")
                problem_seen[iid] = h
                for band in range(4):
                    near_buckets[(band, (h >> (16 * band)) & 0xffff)].append(iid)
            messages = normalize(r["messages"])
            if sum(len(m["content"]) for m in messages) > cfg["max_message_chars"]:
                raise ValueError("oversize_record")
            fingerprint = digest(messages)
            if fingerprint in seen:
                raise ValueError("duplicate_trajectory")
            seen.add(fingerprint)
            if not isinstance(r["resolved"], bool):
                raise ValueError("resolved_must_be_bool")
            patch = normalize_diff(r["patch"])
            item = {"task_id": iid, "traj_id": tid, "repo": repo,
                    "license": license_record["spdx"], "messages": messages,
                    "patch": patch, "resolved": r["resolved"],
                    "upstream_model": r.get("model"), "sha256": fingerprint}
            valid[iid].append(item)
            audits.append({"task_id": iid, "traj_id": tid, "accepted": True})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            audits.append({"task_id": iid, "traj_id": tid, "accepted": False, "reason": str(e)})
    repos = sorted({v[0]["repo"] for v in valid.values()})
    if len(repos) < 2:
        raise ValueError("At least two accepted repositories needed for held-out repository DEV")
    rng.shuffle(repos)
    nval = max(1, min(len(repos) - 1, round(len(repos) * cfg["validation_fraction"])))
    val_repos = set(repos[:nval])
    sft = {"train": [], "val": []}
    dpo = {"train": [], "val": []}
    task_index = []
    for iid, trajectories in sorted(valid.items()):
        rng.shuffle(trajectories)
        split = "val" if trajectories[0]["repo"] in val_repos else "train"
        good = [t for t in trajectories if t["resolved"]]
        bad = [t for t in trajectories if not t["resolved"] and not any(
            word in "\n".join(m["content"] for m in t["messages"][-4:]).lower()
            for word in cfg["failure_patterns"])]
        sft[split].extend(good[:cfg["max_trajectories_per_task"]])
        pairs = []
        for chosen in good:
            for rejected in bad:
                if chosen["patch"] == rejected["patch"]:
                    continue
                shared = common_prefix(chosen["messages"], rejected["messages"])
                # Require identical initial system/user prompt; use only that prefix.
                prompt = []
                for m in shared:
                    if m["role"] not in {"system", "user"}:
                        break
                    prompt.append(m)
                if not prompt or not any(m["role"] == "user" for m in prompt):
                    continue
                prompt = [dict(m) for m in prompt]
                # Preserve issue text, but replace the trajectory-specific interaction
                # instruction with a clearly labeled patch-completion instruction.
                prompt.append({"role": "user", "content": "Return only the final unified diff patch for this issue. Do not modify tests."})
                pairs.append({"task_id": iid, "repo": chosen["repo"], "prompt": prompt,
                    "chosen": "```diff\n" + chosen["patch"] + "```",
                    "rejected": "```diff\n" + rejected["patch"] + "```",
                    "chosen_traj_id": chosen["traj_id"], "rejected_traj_id": rejected["traj_id"],
                    "label_source": "upstream resolved True/False; heuristic environment exclusion",
                    "sha256": digest([iid, chosen["patch"], rejected["patch"]])})
        dpo[split].extend(pairs[:cfg["max_pairs_per_task"]])
        task = tasks[iid]
        task_index.append({"task_id": iid, "repo": trajectories[0]["repo"], "split": split,
             "image_name": task.get("image_name"), "problem_sha256": digest(task["problem_statement"]),
             "n_resolved": len(good), "n_unresolved": len(bad),
             "difficulty_proxy": "hard" if len(good) < len(bad) else "easy_or_medium"})
    for split in ("train", "val"):
        rng.shuffle(sft[split]); rng.shuffle(dpo[split])
    sft["train"] = sft["train"][:cfg["max_sft_trajectories"]]
    dpo["train"] = dpo["train"][:cfg["max_dpo_pairs"]]
    return sft, dpo, audits, task_index


def prepare(filename):
    cfg = config(filename)
    manifest = training_protocol(cfg)
    tasks = load_tasks(cfg["tasks_dir"])
    licenses = read_json(cfg["licenses"])
    sft, dpo, audit, index = build(local_dataset(cfg["trajectories_dir"], cfg["trajectory_split"]),
                                  tasks, cfg, licenses, manifest)
    out = path(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        write_rows(out / f"sft_{split}.jsonl", sft[split])
        write_rows(out / f"dpo_{split}.jsonl", dpo[split])
    write_rows(out / "audit.jsonl", audit)
    write_rows(out / "task_index.jsonl", index)
    stats = {"sft": {k: len(v) for k, v in sft.items()}, "dpo": {k: len(v) for k, v in dpo.items()},
             "rejections": dict(Counter(a["reason"] for a in audit if not a["accepted"])),
             "repositories": len({r["repo"] for r in index}),
             "validation_repositories": sorted({r["repo"] for r in index if r["split"] == "val"}),
             "independent_execution_replay": False}
    write_json(out / "stats.json", stats)
    provenance = {"config": cfg, "experiment_mode": cfg.get("experiment_mode", "formal"), "benchmark_lock": manifest["lock_sha256"],
                  "licenses_sha256": file_hash(path(cfg["licenses"])),
                  "sources": [read_json(path(cfg[k]) / "snapshot_manifest.json")
                              for k in ("tasks_dir", "trajectories_dir")]}
    write_json(out / "provenance.json", provenance)
    print(json.dumps(stats, indent=2))

````

## src/qwen_swesmith/download.py

````python
"""Only this module may contact model/dataset hosts. No training downloads."""
from __future__ import annotations

import os
import json
import urllib.request
from .common import config, path, write_json, file_hash


def download(filename):
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        raise RuntimeError("Download is an online step; unset HF_HUB_OFFLINE first")
    from huggingface_hub import HfApi, snapshot_download
    cfg = config(filename)
    api = HfApi()
    for entry in [cfg["model"], *cfg["datasets"]]:
        kind = entry.get("repo_type", "model")
        revision = entry["revision"]
        info = api.repo_info(entry["repo_id"], repo_type=kind, revision=revision)
        destination = path(entry["local_dir"])
        # Entire snapshot: all original model weights, tokenizer, processor and configs.
        snapshot_download(repo_id=entry["repo_id"], repo_type=kind, revision=info.sha,
                          local_dir=str(destination))
        files = []
        for p in sorted(destination.rglob("*")):
            if not p.is_file() or ".cache" in p.parts or p.name == "snapshot_manifest.json":
                continue
            files.append({"path": p.relative_to(destination).as_posix(),
                          "bytes": p.stat().st_size, "sha256": file_hash(p)})
        write_json(destination / "snapshot_manifest.json", {
            "repo_id": entry["repo_id"], "repo_type": kind,
            "revision": info.sha, "files": files})
        print(f"Saved {entry['repo_id']}@{info.sha} -> {destination}", flush=True)


def original_repo(repo):
    import re
    if repo.startswith("swesmith/"):
        name = repo.split("/", 1)[1]
        name = re.sub(r"\.[0-9a-f]{7,40}$", "", name)
        if "__" not in name:
            raise ValueError(f"Cannot resolve original repo: {repo}")
        return name.replace("__", "/", 1).lower()
    return repo.lower().removesuffix(".git")


def licenses(filename):
    """Metadata lookup only. Code licenses must be reviewed before publication."""
    from .data import load_tasks
    cfg = config(filename)
    tasks = load_tasks(cfg["tasks_dir"])
    records = {}
    for repo in sorted({original_repo(t["repo"]) for t in tasks.values()}):
        url = f"https://api.github.com/repos/{repo}/license"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "qs-license-audit"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
                d = json.load(r)
            records[repo] = {"spdx": d["license"]["spdx_id"],
                             "url": d.get("html_url"), "license_file_sha": d.get("sha"),
                             "basis": "current GitHub metadata; review historical snapshot"}
        except Exception as e:
            records[repo] = {"spdx": "UNKNOWN", "error": type(e).__name__}
        print(repo, records[repo]["spdx"], flush=True)
    write_json(cfg["licenses"], records)

````

## src/qwen_swesmith/encoding.py

````python
"""Assistant-only labels using offsets in the ACTUAL complete rendered template."""
from __future__ import annotations
import re
from .schema import TOOLS


def encode(tok, messages, tools=None, thinking=True, preserve_thinking=True):
    rendered = tok.apply_chat_template(messages, tools=tools, tokenize=False,
        add_generation_prompt=False, enable_thinking=thinking, preserve_thinking=preserve_thinking)
    tokens = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    spans = [(m.start(1), m.end()) for m in re.finditer(
        r"<\|im_start\|>assistant\n(.*?)<\|im_end\|>", rendered, re.DOTALL)]
    if not spans:
        raise ValueError("Official template rendered no complete assistant turns")
    labels = []
    i = 0
    for tid, (start, end) in zip(tokens["input_ids"], tokens["offset_mapping"]):
        while i < len(spans) and start >= spans[i][1]:
            i += 1
        supervised = i < len(spans) and end > start and start >= spans[i][0] and end <= spans[i][1]
        labels.append(tid if supervised else -100)
    labels[0] = -100
    if not any(x != -100 for x in labels):
        raise ValueError("No assistant supervision after tokenization")
    return {"input_ids": tokens["input_ids"], "labels": labels}


def windows(record, max_length, overlap):
    if not 0 <= overlap < max_length - 1:
        raise ValueError("Invalid overlap")
    ids, labels = record["input_ids"], record["labels"]
    stride = max_length - overlap
    end_previous = 0
    for start in range(0, len(ids), stride):
        end = min(start + max_length, len(ids))
        lab = list(labels[start:end])
        # Supervise each source target once; overlap is context only.
        for i in range(min(max(end_previous - start, 1), len(lab))):
            lab[i] = -100
        if any(x != -100 for x in lab[1:]):
            yield {"input_ids": ids[start:end], "labels": lab}
        end_previous = end
        if end == len(ids):
            break


def encode_sft(tok, record, cfg):
    e = encode(tok, record["messages"], tools=TOOLS,
               thinking=cfg["thinking"], preserve_thinking=cfg["preserve_thinking"])
    return list(windows(e, cfg["max_length"], cfg["window_overlap"]))


def encode_pair(tok, record, cfg):
    result = {}
    # One shared prompt and two COMPLETE patches; never truncate the preferred answer.
    for side in ("chosen", "rejected"):
        e = encode(tok, record["prompt"] + [{"role": "assistant", "content": record[side]}],
                   thinking=False, preserve_thinking=cfg["preserve_thinking"])
        if len(e["input_ids"]) > cfg["max_length"]:
            raise ValueError("pair_too_long: increase max_length on a larger GPU; no silent truncation")
        # DPO score must cover ONLY the final completion, not earlier shared assistant turns.
        result[side] = e
    return result


def sequence_logprob(model, example):
    import torch
    import torch.nn.functional as F
    device = model.get_input_embeddings().weight.device
    ids = torch.tensor([example["input_ids"]], dtype=torch.long, device=device)
    labels = torch.tensor(example["labels"], dtype=torch.long, device=device)
    target_positions = torch.where(labels[1:] != -100)[0] + 1
    if target_positions.numel() == 0:
        raise ValueError("No shifted targets")
    # Qwen supports an index tensor: avoid logits for user/tool/context-only positions.
    logits = model(input_ids=ids, attention_mask=torch.ones_like(ids),
                   use_cache=False, logits_to_keep=target_positions - 1).logits[0]
    target = labels[target_positions]
    total = logits.new_zeros((), dtype=torch.float32)
    for offset in range(0, target.numel(), 64):
        total = total - F.cross_entropy(logits[offset:offset + 64].float(),
                                       target[offset:offset + 64], reduction="sum")
    return total, int(target.numel())

````

## src/qwen_swesmith/export.py

````python
from __future__ import annotations
import shutil
from .common import offline, local_dir, path, read_json, write_json
from .model import verify_snapshot


def export(base, destination, adapter=None):
    """Merge on CPU for official vLLM/SGLang evaluation; requires ample HOST RAM."""
    offline()
    root, manifest = verify_snapshot(base, full_hash=True)
    out = path(destination)
    if out.exists():
        raise FileExistsError(out)
    import torch
    from transformers import AutoModelForImageTextToText
    model, info = AutoModelForImageTextToText.from_pretrained(
        str(root), local_files_only=True, trust_remote_code=False, dtype=torch.bfloat16,
        device_map={"": "cpu"}, output_loading_info=True, use_kernels=False)
    print("[export loading report]", info, flush=True)
    if info.get("missing_keys") or info.get("mismatched_keys"):
        raise RuntimeError("Incomplete base weights; abort export")
    if adapter:
        from peft import PeftModel
        a = local_dir(adapter, ("adapter_config.json", "provenance.json"))
        if read_json(a / "provenance.json")["base_revision"] != manifest["revision"]:
            raise ValueError("Adapter/base revision mismatch")
        model = PeftModel.from_pretrained(model, str(a), local_files_only=True)
        model = model.merge_and_unload(safe_merge=True)
    out.mkdir(parents=True)
    model.save_pretrained(str(out), safe_serialization=True, max_shard_size="4GB")
    # Preserve original tokenizer/chat template/processor exactly, including multimodal assets.
    for p in root.iterdir():
        if p.is_file() and (p.suffix in {".json", ".jinja", ".txt", ".model"}) and p.name not in {
            "config.json", "model.safetensors.index.json", "snapshot_manifest.json", "generation_config.json"}:
            shutil.copy2(p, out / p.name)
    write_json(out / "export_provenance.json", {"base_revision": manifest["revision"],
        "adapter": str(path(adapter)) if adapter else None, "loading_report": info,
        "mtp": "MTP/speculative decoding not used; use the same conditional-generation export for all three versions"})

````

## src/qwen_swesmith/inference.py

````python
from __future__ import annotations
import json
import re
import threading
import time
import uuid
from .common import config, seed_all
from .model import load


def parse_output(text, thinking=False):
    reasoning = None
    if "</think>" in text:
        reasoning, text = text.split("</think>", 1)
        reasoning = reasoning.removeprefix("<think>").strip()
    elif thinking and "<tool_call>" not in text:
        # A thinking generation that exhausted its budget before </think>.
        return {"role": "assistant", "content": "", "reasoning_content": text.removeprefix("<think>").strip()}
    calls = []
    for body in re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL):
        fn = re.fullmatch(r"<function=([^>]+)>\s*(.*?)\s*</function>", body, re.DOTALL)
        if not fn:
            raise ValueError("Malformed Qwen tool call")
        args = {}
        for key, value in re.findall(r"<parameter=([^>]+)>\n?(.*?)\n?</parameter>", fn.group(2), re.DOTALL):
            # Tools in this training corpus have known integer/array fields.
            if key in {"insert_line", "view_range"}:
                args[key] = json.loads(value.strip())
            else:
                args[key] = value
        calls.append({"id": "call_" + uuid.uuid4().hex, "type": "function",
                      "function": {"name": fn.group(1), "arguments": json.dumps(args, ensure_ascii=False)}})
    if "<tool_call>" in text and not calls:
        raise ValueError("Unclosed tool call")
    content = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()
    msg = {"role": "assistant", "content": content or None}
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    if calls:
        msg["tool_calls"] = calls
    return msg


class LocalEngine:
    def __init__(self, cfg, adapter=None):
        seed_all(cfg["seed"])
        self.cfg = cfg
        self.model, self.tok, self.details = load(cfg, adapter=adapter, train=False)
        self.mutex = threading.Lock()

    def completion(self, request):
        import torch
        messages = request["messages"]
        for m in messages:
            if not isinstance(m.get("content", ""), (str, type(None))):
                raise ValueError("This lightweight server is text-only; use exported weights with vLLM for image HLE")
        for m in messages:
            for call in m.get("tool_calls", []):
                if isinstance(call["function"].get("arguments"), str):
                    call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        thinking = self.cfg["thinking"]
        # Fixed protocol; requests cannot silently change model-level thinking settings.
        text = self.tok.apply_chat_template(messages, tools=request.get("tools"), tokenize=False,
            add_generation_prompt=True, enable_thinking=thinking,
            preserve_thinking=self.cfg["preserve_thinking"])
        inputs = self.tok(text, return_tensors="pt", add_special_tokens=False).to(
            self.model.get_input_embeddings().weight.device)
        n = inputs["input_ids"].shape[1]
        budget = request.get("max_completion_tokens", request.get("max_tokens", self.cfg["max_tokens"]))
        if not isinstance(budget, int) or budget < 1 or budget > self.cfg["max_tokens"]:
            raise ValueError("Requested output tokens exceed the frozen server budget")
        if n + budget > self.cfg["max_length"]:
            raise ValueError("Input plus output budget exceeds configured context; no silent truncation")
        temperature = request.get("temperature", self.cfg["temperature"])
        top_p = request.get("top_p", self.cfg["top_p"])
        if temperature != self.cfg["temperature"] or top_p != self.cfg["top_p"]:
            raise ValueError("Sampling parameters differ from server protocol")
        generation = {"max_new_tokens": budget, "do_sample": temperature > 0,
                      "pad_token_id": self.tok.pad_token_id, "use_cache": True}
        if temperature > 0:
            generation.update(temperature=temperature, top_p=top_p, top_k=self.cfg["top_k"])
        with self.mutex, torch.inference_mode():
            seed_all(request.get("seed", self.cfg["seed"]))
            output = self.model.generate(**inputs, **generation)
        ids = output[0, n:]
        message = parse_output(self.tok.decode(ids, skip_special_tokens=True), thinking=thinking)
        return {"id": "chatcmpl-" + uuid.uuid4().hex, "object": "chat.completion",
                "created": int(time.time()), "model": request.get("model", "local-qwen"),
                "choices": [{"index": 0, "message": message,
                             "finish_reason": "tool_calls" if message.get("tool_calls") else
                             ("length" if len(ids) == budget else "stop")}],
                "usage": {"prompt_tokens": n, "completion_tokens": len(ids), "total_tokens": n + len(ids)}}


def serve(filename, adapter=None):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    import uvicorn
    cfg = config(filename)
    engine = LocalEngine(cfg, adapter)
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok", "base_revision": engine.details["base_revision"]}

    @app.get("/v1/models")
    def models():
        return {"object": "list", "data": [{"id": "local-qwen", "object": "model", "owned_by": "local"}]}

    @app.post("/v1/chat/completions")
    def completion(body: dict):
        try:
            response = engine.completion(body)
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if not body.get("stream"):
            return response
        # Protocol-compatible buffered SSE, NOT token-by-token streaming.
        def chunks():
            shared = {k: response[k] for k in ("id", "created", "model")}
            yield "data: " + json.dumps({**shared, "object": "chat.completion.chunk", "choices": [
                {"index": 0, "delta": response["choices"][0]["message"], "finish_reason": None}]}) + "\n\n"
            yield "data: " + json.dumps({**shared, "object": "chat.completion.chunk", "choices": [
                {"index": 0, "delta": {}, "finish_reason": response["choices"][0]["finish_reason"]}],
                "usage": response["usage"]}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(chunks(), media_type="text/event-stream")
    uvicorn.run(app, host=cfg["host"], port=cfg["port"], workers=1)

````

## src/qwen_swesmith/model.py

````python
from __future__ import annotations
import json
import re
from .common import offline, local_dir, read_json, path, file_hash

ATTENTION_SUFFIXES = {"q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z",
                      "in_proj_a", "in_proj_b", "out_proj"}


def verify_snapshot(base, full_hash=False):
    root = local_dir(base, ("config.json", "tokenizer_config.json", "snapshot_manifest.json"))
    manifest = read_json(root / "snapshot_manifest.json")
    if manifest["repo_id"] != "Qwen/Qwen3.6-35B-A3B":
        raise ValueError("Only the designated Qwen3.6-35B-A3B is allowed")
    for f in manifest["files"]:
        p = root / f["path"]
        if not p.is_file() or p.stat().st_size != f["bytes"]:
            raise ValueError(f"Incomplete local snapshot: {p}")
        if full_hash or p.suffix in {".json", ".jinja"}:
            if file_hash(p) != f["sha256"]:
                raise ValueError(f"Local snapshot modified: {p}")
    return root, manifest


def memory_estimate(model_config, context=2048):
    t = model_config.get("text_config", model_config)
    experts = t["num_hidden_layers"] * t["num_experts"] * 3 * t["hidden_size"] * t["moe_intermediate_size"]
    layers = sum(x == "full_attention" for x in t["layer_types"])
    kv = layers * 2 * t["num_key_value_heads"] * t["head_dim"] * context * 2
    return {"routed_expert_parameters": experts,
            "routed_experts_bf16_gib": experts * 2 / 2**30,
            "35b_bf16_weight_estimate_gib": 35e9 * 2 / 2**30,
            "35b_ideal_4bit_weight_lower_bound_gib": 35e9 * 0.5 / 2**30,
            "full_attention_kv_cache_gib_batch1_bf16": kv / 2**30,
            "note": "Excludes vision/mtp differences, linear-attention state, activations, logits, optimizer, allocator and quantization overhead."}


def tokenizer(base):
    offline()
    from transformers import AutoTokenizer
    root = local_dir(base, ("config.json", "tokenizer_config.json"))
    tok = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False, use_fast=True)
    if not tok.is_fast or not tok.chat_template:
        raise ValueError("A fast tokenizer with the pinned official chat template is required")
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    return tok


def load(cfg, adapter=None, train=False, with_reference=False):
    offline()
    root, manifest = verify_snapshot(cfg["base_dir"], full_hash=cfg.get("verify_full_hash", False))
    import torch
    from transformers import AutoModelForImageTextToText
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required; this project does not silently fall back to CPU")
    if torch.cuda.device_count() != 1:
        raise RuntimeError("Use CUDA_VISIBLE_DEVICES to select ONE GPU. Multi-GPU training needs a separately validated FSDP/TP backend.")
    estimate = memory_estimate(read_json(root / "config.json"), cfg.get("max_length", 2048))
    mode = cfg.get("quantization", "bf16")
    if mode != "bf16":
        raise RuntimeError("Standard bitsandbytes is not a verified packed-MoE quantizer for this implementation. "
                           "Do not assume all 35B weights become NF4. This backend supports BF16 only; see docs/HARDWARE.md.")
    free, total = torch.cuda.mem_get_info()
    lower = estimate["35b_bf16_weight_estimate_gib"] + cfg.get("reserve_gib", 8)
    if free / 2**30 < lower:
        raise RuntimeError(f"Insufficient free VRAM: {free / 2**30:.1f} GiB; "
                           f"estimated weights + reserve {lower:.1f} GiB. 24GB/48GB are not supported here.")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("BF16-capable CUDA GPU required")
    model, info = AutoModelForImageTextToText.from_pretrained(
        str(root), local_files_only=True, trust_remote_code=False, dtype=torch.bfloat16,
        device_map={"": 0}, attn_implementation=cfg.get("attention_backend", "sdpa"),
        output_loading_info=True, use_kernels=False)
    # Keep actual missing/unexpected lists visible and save them in run metadata.
    print("[base loading report]", json.dumps(info, default=str), flush=True)
    if info.get("missing_keys") or info.get("mismatched_keys"):
        raise RuntimeError("Missing/mismatched model weights; inspect the loading report before training")
    for p in model.parameters():
        p.requires_grad_(False)
    targets = [name for name, module in model.named_modules()
               if isinstance(module, torch.nn.Linear)
               and name.rsplit(".", 1)[-1] in ATTENTION_SUFFIXES
               and ("self_attn" in name or "linear_attn" in name)]
    if not targets:
        raise RuntimeError("No expected language attention targets found; architecture may have changed")
    packed = [{"name": n, "shape": list(p.shape)} for n, p in model.named_parameters()
              if ".experts." in n and p.ndim == 3]
    if adapter:
        from peft import PeftModel
        a = local_dir(adapter, ("adapter_config.json", "adapter_model.safetensors", "provenance.json"))
        ap = read_json(a / "provenance.json")
        if ap["base_revision"] != manifest["revision"]:
            raise ValueError("Adapter/base revision mismatch")
        model = PeftModel.from_pretrained(model, str(a), is_trainable=train,
                                         adapter_name="default", local_files_only=True)
        if with_reference:
            model.load_adapter(str(a), adapter_name="reference", is_trainable=False, local_files_only=True)
            set_active(model, "default")
    elif train:
        from peft import LoraConfig, get_peft_model
        lora = cfg["lora"]
        model = get_peft_model(model, LoraConfig(r=lora["rank"], lora_alpha=lora["alpha"],
                    lora_dropout=0.0, target_modules=targets, bias="none", task_type="CAUSAL_LM"))
    if train:
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        # DPO replay gradients assume deterministic forwards. Disable all dropout.
        for module in model.modules():
            if isinstance(module, torch.nn.Dropout):
                module.p = 0.0
        model.train()
    else:
        model.eval()
        model.config.use_cache = True
    details = {"base_revision": manifest["revision"], "base_dir": str(root),
               "chat_template_sha256": file_hash(root / "tokenizer_config.json"),
               "quantization": mode, "targets": targets, "packed_experts_frozen": packed,
               "loading_report": info, "gpu": torch.cuda.get_device_name(0),
               "gpu_total_gib": total / 2**30, "memory_estimate": estimate,
               "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
               "model_class": type(model).__name__}
    return model, tokenizer(root), details


def set_active(model, name):
    model.set_adapter(name)
    # PEFT set_adapter can re-enable adapter gradients. Reference remains frozen.
    for n, p in model.named_parameters():
        p.requires_grad_(name == "default" and "lora_" in n and ".default." in n)

````

## src/qwen_swesmith/portable.py

````python
"""Cross-platform process/log handling and user-friendly command names."""
from __future__ import annotations
import argparse
import importlib.util
import os
import platform
import subprocess
import sys
from .common import ROOT, config, path


class Tee:
    def __init__(self, original, logfile):
        self.original = original
        self.logfile = logfile
        self.encoding = "utf-8"

    def write(self, value):
        self.original.write(value)
        self.logfile.write(value)
        self.flush()
        return len(value)

    def flush(self):
        self.original.flush()
        self.logfile.flush()

    def isatty(self):
        return False


def require_dependencies():
    missing = [name for name in ("yaml", "numpy", "torch", "transformers", "peft", "datasets")
               if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError("Missing packages: " + ", ".join(missing) +
                           ". Run: python setup_env.py --cuda cu128")


def logged_train(filename):
    from .train import train
    cfg = config(filename)
    p = path(cfg["output_dir"]).parent / "console" / (path(cfg["output_dir"]).name + ".log")
    p.parent.mkdir(parents=True, exist_ok=True)
    stdout, stderr = sys.stdout, sys.stderr
    with p.open("a", encoding="utf-8") as f:
        try:
            sys.stdout, sys.stderr = Tee(stdout, f), Tee(stderr, f)
            print(f"Platform: {platform.platform()}; config: {filename}", flush=True)
            train(filename)
        except Exception:
            import traceback
            traceback.print_exc()
            raise
        finally:
            sys.stdout, sys.stderr = stdout, stderr


def main():
    parser = argparse.ArgumentParser(description="Qwen3.6 + SWE-smith: native Windows/Linux Python launcher")
    sub = parser.add_subparsers(dest="command", required=True)
    defaults = {"download": "configs/download.yaml", "licenses": "configs/data.yaml",
                "prepare": "configs/data.yaml", "sft": "configs/sft_80gb.yaml",
                "stage2": "configs/stage2_80gb.yaml", "serve": "configs/inference.yaml"}
    for name, filename in defaults.items():
        p = sub.add_parser(name)
        p.add_argument("--config", default=filename)
        if name in {"sft", "stage2", "serve"}:
            p.add_argument("--gpu", default="0", help="CUDA device to expose; one GPU for this trainer")
        if name == "serve":
            p.add_argument("--adapter")
    p = sub.add_parser("train-all")
    p.add_argument("--data-config", default="configs/data.yaml")
    p.add_argument("--sft-config", default="configs/sft_80gb.yaml")
    p.add_argument("--stage2-config", default="configs/stage2_80gb.yaml")
    p.add_argument("--gpu", default="0")
    p = sub.add_parser("curves"); p.add_argument("--run-dir", required=True)
    p = sub.add_parser("export")
    p.add_argument("--base", default="assets/models/Qwen3.6-35B-A3B")
    p.add_argument("--adapter"); p.add_argument("--output", required=True)
    for name in ("freeze", "summarize", "evaluate"):
        p = sub.add_parser(name); p.add_argument("--manifest", default="benchmarks/manifest.json")
        if name == "evaluate":
            p.add_argument("--variant", choices=["base", "sft", "stage2"], required=True)
            p.add_argument("--benchmark", default="all")
            p.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    p = sub.add_parser("vllm")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--tp", type=int, default=1)
    p.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if getattr(args, "gpu", None) is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("PYTHONUTF8", "1")
    if args.command == "vllm":
        if os.name == "nt":
            raise RuntimeError("vLLM official CUDA backend requires Linux. Use the same project on a Linux GPU server/WSL2, "
                               "or use 'python run.py serve' for native Windows text-only local inference.")
        root = path(args.model_dir)
        if not (root / "export_provenance.json").is_file():
            raise FileNotFoundError("Run python run.py export first; provide the LOCAL exported directory")
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        cmd = [sys.executable, "-m", "vllm.entrypoints.cli.main", "serve", str(root),
               "--served-model-name", "local-qwen", "--dtype", "bfloat16", "--tensor-parallel-size", str(args.tp),
               "--max-model-len", "262144", "--max-num-seqs", "1", "--gpu-memory-utilization", "0.90",
               "--reasoning-parser", "qwen3", "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_coder",
               "--host", "127.0.0.1", "--port", str(args.port)]
        raise SystemExit(subprocess.call(cmd, cwd=ROOT))
    require_dependencies()
    if args.command in {"download", "licenses"}:
        from .download import download, licenses
        (download if args.command == "download" else licenses)(args.config)
    elif args.command == "prepare":
        from .data import prepare
        prepare(args.config)
    elif args.command in {"sft", "stage2"}:
        expected = "sft" if args.command == "sft" else "dpo"
        if config(args.config)["stage"] != expected:
            raise ValueError("Config stage does not match the command")
        logged_train(args.config)
    elif args.command == "train-all":
        from .data import prepare
        from .analysis import curves
        prepare(args.data_config)
        logged_train(args.sft_config); curves(config(args.sft_config)["output_dir"])
        logged_train(args.stage2_config); curves(config(args.stage2_config)["output_dir"])
    elif args.command == "serve":
        from .inference import serve
        serve(args.config, args.adapter)
    elif args.command == "curves":
        from .analysis import curves
        curves(args.run_dir)
    elif args.command == "export":
        from .export import export
        export(args.base, args.output, args.adapter)
    elif args.command == "freeze":
        from .benchmarks import freeze
        freeze(args.manifest)
    elif args.command == "evaluate":
        from .benchmarks import run, NAMES
        for name in NAMES if args.benchmark == "all" else (args.benchmark,):
            run(args.manifest, name, args.variant, args.endpoint)
    elif args.command == "summarize":
        from .analysis import summarize
        summarize(args.manifest)

````

## src/qwen_swesmith/preflight.py

````python
from __future__ import annotations
import importlib.metadata
import sys
from .common import config, read_json, write_json, path
from .model import verify_snapshot, memory_estimate


def preflight(filename, inspect=False):
    cfg = config(filename)
    root, manifest = verify_snapshot(cfg["base_dir"], full_hash=cfg.get("verify_full_hash", False))
    report = {"python": sys.version, "base_revision": manifest["revision"],
              "memory": memory_estimate(read_json(root / "config.json"), cfg["max_length"]), "versions": {}}
    for name in ("torch", "transformers", "peft", "accelerate", "datasets", "huggingface-hub", "tokenizers"):
        try:
            report["versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            report["versions"][name] = "MISSING"
    import torch
    report["cuda_available"] = torch.cuda.is_available()
    report["gpus"] = [{"name": torch.cuda.get_device_name(i),
                       "total_gib": torch.cuda.get_device_properties(i).total_memory / 2**30}
                      for i in range(torch.cuda.device_count())]
    if inspect:
        from .common import offline
        offline()
        from accelerate import init_empty_weights
        from transformers import AutoConfig, AutoModelForImageTextToText
        with init_empty_weights():
            model = AutoModelForImageTextToText.from_config(
                AutoConfig.from_pretrained(str(root), local_files_only=True, trust_remote_code=False))
        report["parameter_count"] = sum(p.numel() for p in model.parameters())
        report["packed_experts"] = [{"name": n, "shape": list(p.shape)} for n, p in model.named_parameters()
                                    if ".experts." in n and p.ndim == 3]
        report["modules"] = [{"name": n, "class": type(m).__name__} for n, m in model.named_modules()
                             if "self_attn" in n or "linear_attn" in n]
    write_json("outputs/preflight.json", report)
    import json
    print(json.dumps(report, indent=2))
    if not report["cuda_available"]:
        raise RuntimeError("CUDA GPU missing")
    if cfg.get("quantization") != "bf16":
        raise RuntimeError("Packed-expert NF4 is not verified; use BF16 on a larger GPU")
    required = report.get("parameter_count", 35e9) * 2 / 2**30 + cfg.get("reserve_gib", 8)
    free = torch.cuda.mem_get_info()[0] / 2**30
    if free < required:
        raise RuntimeError(f"Need approximately {required:.1f} GiB free; available {free:.1f}. See docs/HARDWARE.md")

````

## src/qwen_swesmith/schema.py

````python
"""Normalize actual SWE-smith tool split, not an invented train split."""
from __future__ import annotations
import json
import re

TOOLS = [
    {"type": "function", "function": {"name": "bash", "description": "Execute a bash command in the task container.",
      "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "str_replace_editor", "description": "View or edit a text file in the task container.",
      "parameters": {"type": "object", "properties": {
          "command": {"type": "string", "enum": ["view", "create", "str_replace", "insert", "undo_edit"]},
          "path": {"type": "string"}, "file_text": {"type": "string"}, "old_str": {"type": "string"},
          "new_str": {"type": "string"}, "insert_line": {"type": "integer"},
          "view_range": {"type": "array", "items": {"type": "integer"}}}, "required": ["command", "path"]}}},
    {"type": "function", "function": {"name": "submit", "description": "End the task.",
      "parameters": {"type": "object", "properties": {}}}},
]


def text_content(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(v, dict) and v.get("type") == "text" for v in value):
        return "\n".join(v["text"] for v in value)
    raise ValueError("Non-text or malformed message content")


def normalize(raw):
    raw = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(raw, list) or not raw:
        raise ValueError("messages must be a nonempty list")
    result = []
    outstanding = set()
    names = {t["function"]["name"] for t in TOOLS}
    for item in raw:
        role = item["role"]
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"Unsupported role: {role}")
        content = text_content(item.get("content"))
        if "<|im_start|>" in content or "<|im_end|>" in content:
            raise ValueError("Chat control tokens inside content")
        m = {"role": role, "content": content}
        if role == "assistant":
            if outstanding:
                raise ValueError("Tool response missing before next assistant")
            calls = item.get("tool_calls") or []
            cleaned = []
            for call in calls:
                fn = call["function"]
                if fn["name"] not in names:
                    raise ValueError(f"Unknown tool {fn['name']}")
                args = fn["arguments"]
                args = json.loads(args) if isinstance(args, str) else args
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be object")
                cid = call["id"]
                cleaned.append({"id": cid, "type": "function", "function": {"name": fn["name"], "arguments": args}})
                outstanding.add(cid)
            if cleaned:
                m["tool_calls"] = cleaned
        elif role == "tool":
            ids = item.get("tool_call_ids") or [item.get("tool_call_id")]
            if len(ids) != 1 or ids[0] not in outstanding:
                raise ValueError("Ambiguous or orphan tool response")
            m["tool_call_id"] = ids[0]
            outstanding.remove(ids[0])
        result.append(m)
    # submit can terminate without a tool observation.
    if outstanding:
        terminal = result[-1].get("tool_calls", [])
        if not terminal or any(c["function"]["name"] != "submit" for c in terminal):
            raise ValueError("Unfinished tool calls")
    if not any(m["role"] == "assistant" for m in result):
        raise ValueError("No assistant turns")
    return result


def normalize_diff(patch):
    if not isinstance(patch, str) or not patch.strip():
        raise ValueError("Empty patch")
    if "diff --git " not in patch or "@@ " not in patch:
        raise ValueError("Not a unified diff")
    return patch.strip() + "\n"


def simhash(text):
    import hashlib
    words = re.findall(r"\w+", text.lower())
    shingles = {" ".join(words[i:i + 5]) for i in range(max(1, len(words) - 4))}
    vector = [0] * 64
    for s in shingles:
        h = int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += 1 if (h >> bit) & 1 else -1
    return sum((1 << bit) for bit, score in enumerate(vector) if score > 0)

````

## src/qwen_swesmith/train.py

````python
"""Single-GPU BF16 attention LoRA. DPO shares the frozen base with SFT reference."""
from __future__ import annotations
import math
import random
import time
import shutil
from .common import config, rows, path, write_json, read_json, snapshot, seed_all, file_hash
from .benchmarks import training_protocol
from .model import load, set_active
from .encoding import encode_sft, encode_pair, sequence_logprob


def lr_factor(step, warmup, total):
    if step < warmup:
        return (step + 1) / max(warmup, 1)
    progress = (step - warmup) / max(total - warmup, 1)
    return 0.5 * (1 + math.cos(math.pi * min(progress, 1)))


def stream_examples(examples, seed):
    rng = random.Random(seed)
    while True:
        order = list(range(len(examples)))
        rng.shuffle(order)
        for i in order:
            yield examples[i]


def tokenized(tok, records, cfg):
    accepted, rejected = [], []
    for r in records:
        try:
            encoded = encode_sft(tok, r, cfg) if cfg["stage"] == "sft" else [encode_pair(tok, r, cfg)]
            accepted.extend(encoded)
        except (ValueError, TypeError, KeyError) as e:
            rejected.append({"task_id": r["task_id"], "reason": str(e)})
    return accepted, rejected


def dpo_measure(model, pair, beta):
    import torch
    with torch.no_grad():
        set_active(model, "reference")
        rc, _ = sequence_logprob(model, pair["chosen"])
        rr, _ = sequence_logprob(model, pair["rejected"])
        set_active(model, "default")
        pc, nc = sequence_logprob(model, pair["chosen"])
        pr, nr = sequence_logprob(model, pair["rejected"])
        margin = beta * ((pc - pr) - (rc - rr))
        loss = torch.nn.functional.softplus(-margin)
        # d(loss)/d(log pi chosen); rejected coefficient is its opposite.
        coeff = beta * (torch.sigmoid(margin) - 1)
    return {"loss": float(loss), "chosen_reward": float(beta * (pc - rc)),
            "rejected_reward": float(beta * (pr - rr)), "preference_accuracy": float(margin > 0),
            "coefficient": coeff.detach(), "tokens": nc + nr}


def train_micro(model, example, cfg):
    if cfg["stage"] == "sft":
        lp, n = sequence_logprob(model, example)
        loss = -lp / n
        (loss / cfg["gradient_accumulation"]).backward()
        return {"loss": float(loss.detach()), "tokens": n}
    metrics = dpo_measure(model, example, cfg["beta"])
    # Replay one candidate at a time. Same exact DPO gradient, lower peak graph memory.
    for side, sign in (("chosen", 1), ("rejected", -1)):
        lp, _ = sequence_logprob(model, example[side])
        (sign * metrics["coefficient"] * lp / cfg["gradient_accumulation"]).backward()
    metrics.pop("coefficient")
    return metrics


def evaluate(model, examples, cfg):
    import torch
    model.eval()
    sums = {}
    count = 0
    with torch.no_grad():
        for e in examples:
            if cfg["stage"] == "sft":
                lp, n = sequence_logprob(model, e)
                # Token-weighted validation NLL.
                sums["loss"] = sums.get("loss", 0) - float(lp)
                count += n
            else:
                metrics = dpo_measure(model, e, cfg["beta"])
                for k, v in metrics.items():
                    if k not in {"coefficient", "tokens"}:
                        sums[k] = sums.get(k, 0) + v
                count += 1
    model.train()
    if cfg["stage"] == "dpo":
        set_active(model, "default")
    return {k: v / count for k, v in sums.items()}


def save_adapter(model, tok, destination, details, cfg, step, metric):
    destination = path(destination)
    # Only overwrite checkpoints inside the current run directory.
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    model.save_pretrained(str(destination), selected_adapters=["default"], safe_serialization=True)
    tok.save_pretrained(str(destination))
    write_json(destination / "provenance.json", {
        "base_revision": details["base_revision"], "base_repo": "Qwen/Qwen3.6-35B-A3B",
        "stage": cfg["stage"], "experiment_mode": cfg.get("experiment_mode", "formal"), "step": step, "selection_metric": metric,
        "initial_adapter": cfg.get("initial_adapter"), "quantization": cfg["quantization"],
        "benchmark_lock": details["benchmark_lock"], "data_sha256": details["data_sha256"],
        "targets": details["targets"]})


def train(filename):
    cfg = config(filename)
    if cfg["stage"] not in {"sft", "dpo"}:
        raise ValueError("stage must be sft or dpo")
    manifest = training_protocol(cfg)
    provenance = read_json(cfg["data_provenance"])
    if provenance["benchmark_lock"] != manifest["lock_sha256"]:
        raise ValueError("Data was prepared under a different benchmark lock")
    for k in ("max_steps", "gradient_accumulation", "eval_every", "save_every"):
        if not isinstance(cfg[k], int) or cfg[k] < 1:
            raise ValueError(f"{k} must be positive integer")
    if cfg["stage"] == "dpo" and cfg["beta"] <= 0:
        raise ValueError("DPO beta must be positive")
    out = snapshot(cfg["output_dir"], cfg)
    start = time.time()
    train_seconds = 0.0
    val_seconds = 0.0
    total_targets = 0
    status = "failed"
    step = 0
    try:
        from .common import offline
        offline()
        seed_all(cfg["seed"])
        import torch
        model, tok, details = load(cfg, adapter=cfg.get("initial_adapter"), train=True,
                                   with_reference=cfg["stage"] == "dpo")
        details.update(benchmark_lock=manifest["lock_sha256"],
                       data_sha256={k: file_hash(path(cfg[k])) for k in ("train_file", "val_file")})
        write_json(out / "model_details.json", details)
        train_rows = list(rows(cfg["train_file"]))
        val_rows = list(rows(cfg["val_file"]))
        # Repository DEV isolation, including all preference trajectories of a task.
        if {r["repo"] for r in train_rows} & {r["repo"] for r in val_rows}:
            raise ValueError("Training and validation repository overlap")
        training, rejected_train = tokenized(tok, train_rows, cfg)
        validation, rejected_val = tokenized(tok, val_rows, cfg)
        if cfg.get("max_val_examples", 0):
            validation = validation[:cfg["max_val_examples"]]
        write_json(out / "tokenization_audit.json", {"train_examples": len(training),
            "val_examples": len(validation), "train_rejected": rejected_train, "val_rejected": rejected_val,
            "sft_context_policy": "overlapping token windows; prior system/issue may be absent in later windows",
            "dpo_context_policy": "complete patch pair; oversized pairs excluded, never truncated"})
        if not training or not validation:
            raise ValueError("No usable TRAIN/DEV examples; inspect tokenization_audit.json, increase context or fix data")
        params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
        examples = stream_examples(training, cfg["seed"])
        best = float("inf")
        torch.cuda.reset_peak_memory_stats()
        with (out / "metrics.jsonl").open("w", encoding="utf-8") as log:
            def emit(r):
                import json
                log.write(json.dumps(r) + "\n"); log.flush()
                print(json.dumps(r), flush=True)
            t = time.time()
            initial = evaluate(model, validation, cfg)
            val_seconds += time.time() - t
            emit({"step": 0, "split": "val", **initial, "checkpoint": "initial"})
            best = initial["loss"]
            save_adapter(model, tok, out / "best_adapter", details, cfg, 0, initial)
            for step in range(1, cfg["max_steps"] + 1):
                t = time.time()
                opt.zero_grad(set_to_none=True)
                sums = {}
                for _ in range(cfg["gradient_accumulation"]):
                    metrics = train_micro(model, next(examples), cfg)
                    total_targets += metrics["tokens"]
                    for k, v in metrics.items():
                        if k != "tokens":
                            sums[k] = sums.get(k, 0) + v
                torch.nn.utils.clip_grad_norm_(params, cfg["max_grad_norm"])
                lr = cfg["learning_rate"] * lr_factor(step - 1, cfg["warmup_steps"], cfg["max_steps"])
                for group in opt.param_groups:
                    group["lr"] = lr
                opt.step()
                torch.cuda.synchronize()
                elapsed = time.time() - t
                train_seconds += elapsed
                emit({"step": step, "split": "train", "lr": lr,
                      **{k: v / cfg["gradient_accumulation"] for k, v in sums.items()},
                      "seconds": elapsed, "peak_allocated_gib": torch.cuda.max_memory_allocated() / 2**30,
                      "peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30,
                      "target_tokens_per_second": total_targets / train_seconds})
                metric = None
                if step % cfg["eval_every"] == 0 or step == cfg["max_steps"]:
                    t = time.time()
                    metric = evaluate(model, validation, cfg)
                    val_seconds += time.time() - t
                    emit({"step": step, "split": "val", **metric, "checkpoint": f"step_{step:06d}"})
                    if metric["loss"] < best:
                        best = metric["loss"]
                        save_adapter(model, tok, out / "best_adapter", details, cfg, step, metric)
                if step % cfg["save_every"] == 0:
                    save_adapter(model, tok, out / f"step_{step:06d}", details, cfg, step, metric)
            save_adapter(model, tok, out / "final_adapter", details, cfg, step, metric)
        status = "completed"
    finally:
        elapsed = time.time() - start
        gpu_hours = elapsed / 3600
        write_json(out / "resources.json", {"status": status, "completed_steps": step,
            "wall_seconds": elapsed, "training_seconds": train_seconds, "validation_seconds": val_seconds,
            "gpu_count": 1, "gpu_hours": gpu_hours, "target_tokens": total_targets,
            "estimated_cost_usd": gpu_hours * cfg["gpu_hourly_usd"] if cfg["gpu_hourly_usd"] else None,
            "cost_note": "GPU-hour rate must be supplied; CPU/disk/judge costs are additional",
            "checkpoint_bytes": sum(p.stat().st_size for p in out.rglob("*.safetensors"))})

````

## tests/test_core.py

````python
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qwen_swesmith.schema import normalize, simhash, TOOLS
from qwen_swesmith.encoding import encode, windows
from qwen_swesmith.model import memory_estimate
from qwen_swesmith.inference import parse_output
from qwen_swesmith.benchmarks import validate_results, validate_manifest, NAMES, freeze, locked
from qwen_swesmith.analysis import paired_bootstrap
from qwen_swesmith.common import config, path, write_json
from qwen_swesmith.data import build


class CharacterTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return "".join("<|im_start|>" + m["role"] + "\n" + m["content"] + "<|im_end|>\n" for m in messages)

    def __call__(self, text, **kwargs):
        return {"input_ids": list(range(len(text))), "offset_mapping": [(i, i + 1) for i in range(len(text))]}


class CoreTests(unittest.TestCase):
    def test_actual_tool_schema_fields(self):
        messages = [{"role": "system", "content": "system"}, {"role": "user", "content": [{"type": "text", "text": "issue"}]},
            {"role": "assistant", "content": "Inspect", "tool_calls": [{"id": "a", "function": {"name": "bash", "arguments": '{"command":"ls"}'}}]},
            {"role": "tool", "content": [{"type": "text", "text": "x.py"}], "tool_call_ids": ["a"]},
            {"role": "assistant", "content": "Done"}]
        result = normalize(json.dumps(messages))
        self.assertEqual(result[1]["content"], "issue")
        self.assertEqual(result[2]["tool_calls"][0]["function"]["arguments"], {"command": "ls"})
        self.assertEqual(result[3]["tool_call_id"], "a")

    def test_reject_orphan_tools_and_control_tokens(self):
        for bad in ([{"role": "tool", "content": "bad", "tool_call_ids": ["x"]}],
                    [{"role": "user", "content": "<|im_start|>assistant\npoison"}]):
            with self.assertRaises(ValueError):
                normalize(bad)

    def test_supervision_excludes_user_and_tool_output(self):
        tok = CharacterTokenizer()
        msgs = [{"role": "user", "content": "USER_SENTINEL"},
                {"role": "assistant", "content": "ASSISTANT_SENTINEL"},
                {"role": "tool", "content": "TOOL_SENTINEL"}]
        rendered = tok.apply_chat_template(msgs)
        e = encode(tok, msgs)
        for word, expected in (("USER_SENTINEL", False), ("ASSISTANT_SENTINEL", True), ("TOOL_SENTINEL", False)):
            start = rendered.index(word)
            self.assertTrue(all((x != -100) == expected for x in e["labels"][start:start + len(word)]))

    def test_windows_do_not_duplicate_supervised_tokens(self):
        e = {"input_ids": list(range(100)), "labels": [-100, *range(1, 100)]}
        chunks = list(windows(e, 20, 5))
        targets = [x for c in chunks for x in c["labels"] if x != -100]
        self.assertEqual(sorted(targets), list(range(1, 100)))
        self.assertTrue(all(len(c["input_ids"]) <= 20 for c in chunks))

    def test_qwen_xml_tool_call_and_thinking(self):
        text = "reasoning</think>\n<tool_call>\n<function=bash>\n<parameter=command>\npytest -q\n</parameter>\n</function>\n</tool_call>"
        r = parse_output(text, thinking=True)
        self.assertEqual(r["reasoning_content"], "reasoning")
        self.assertEqual(json.loads(r["tool_calls"][0]["function"]["arguments"]), {"command": "pytest -q"})
        self.assertIsNone(r["content"])
        self.assertEqual(parse_output("unfinished reasoning", thinking=True)["content"], "")

    def test_24gb_and_hybrid_cache_estimates(self):
        cfg = {"text_config": {"num_hidden_layers": 40, "num_experts": 256, "hidden_size": 2048,
                 "moe_intermediate_size": 512, "layer_types": ["linear_attention"] * 30 + ["full_attention"] * 10,
                 "num_key_value_heads": 2, "head_dim": 256}}
        e = memory_estimate(cfg, 262144)
        self.assertGreater(e["routed_experts_bf16_gib"], 24)
        self.assertAlmostEqual(e["full_attention_kv_cache_gib_batch1_bf16"], 5)

    def test_paired_bootstrap_keeps_task_pairing(self):
        result, draws = paired_bootstrap([0, 1, 0, 1], [0.1, 1.1, 0.1, 1.1], repeats=200)
        self.assertAlmostEqual(result["delta_percentage_points"], 10)
        self.assertTrue(all(abs(v - 10) < 1e-9 for v in draws))

    def test_complete_evaluation_no_silent_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            evidence = Path(d) / "raw.json"; evidence.write_text("{}")
            r = {"task_id": "a", "seed": 42, "score": None, "status": "environment_error",
                 "seconds": 1.0, "cost_usd": None, "raw_evidence": str(evidence)}
            validate_results([r], ["a"], 42)
            with self.assertRaises(ValueError): validate_results([r], ["a", "b"], 42)
            with self.assertRaises(ValueError): validate_results([r, r], ["a"], 42)
            with self.assertRaises(ValueError): validate_results([{**r, "status": "ok"}], ["a"], 42)

    def test_unconfirmed_official_versions_block_training(self):
        with self.assertRaises(ValueError):
            validate_manifest(json.loads(path("benchmarks/manifest.json").read_text()))

    def test_data_repository_split_and_same_task_preferences(self):
        cfg = config("configs/data.yaml")
        cfg["min_problem_chars"] = 20
        tasks = {
            "a": {"instance_id": "a", "repo": "owner/alpha", "problem_statement": "network packet serialization socket protocol bytes retry timeout parser failure"},
            "b": {"instance_id": "b", "repo": "owner/beta", "problem_statement": "geometry polygon vertex triangulation orientation coordinate shape area error"}}
        licenses = {r: {"spdx": "MIT"} for r in ("owner/alpha", "owner/beta")}
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"
        records = []
        for iid in tasks:
            for resolved in (True, False):
                messages = [{"role": "system", "content": "Solve the issue"},
                            {"role": "user", "content": tasks[iid]["problem_statement"]},
                            {"role": "assistant", "content": "Fixed" if resolved else "Failed"}]
                records.append({"instance_id": iid, "traj_id": iid + str(resolved), "resolved": resolved,
                                "messages": json.dumps(messages), "patch": diff if resolved else diff.replace("+b", "+c")})
        manifest = {"excluded_repositories": [], "public_prompt_files": [], "benchmarks": {"x": {"task_ids_file": "ids"}}}
        with patch("qwen_swesmith.data.read_json", return_value=[]):
            sft, dpo, audit, index = build(records, tasks, cfg, licenses, manifest)
        self.assertEqual(len(sft["train"]), 1); self.assertEqual(len(sft["val"]), 1)
        self.assertEqual(len(dpo["train"]), 1); self.assertEqual(len(dpo["val"]), 1)
        self.assertFalse({r["repo"] for r in sft["train"]} & {r["repo"] for r in sft["val"]})
        self.assertNotEqual(dpo["train"][0]["chosen"], dpo["train"][0]["rejected"])
        self.assertTrue(all(a["accepted"] for a in audit))

    def test_frozen_manifest_detects_config_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ids = root / "ids.json"; write_json(ids, ["a"])
            agent = {"thinking": True, "preserve_thinking": True, "quantization": "bf16",
                     "context_length": 262144, "temperature": 1.0, "top_p": 0.95, "top_k": 20,
                     "max_tokens": 80000, "tools": [], "prompt_sha256": "a" * 64,
                     "timeout_seconds": 10800, "cpus": 32, "ram_gb": 48,
                     "framework": "Harbor", "agent": "Terminus-2", "includes_images": False,
                     "answer_extraction": "fixed", "judge_version": "fixed"}
            af = root / "agent.json"; write_json(af, agent)
            m = {"frozen": False, "excluded_repositories": [], "benchmarks": {}}
            for name in NAMES:
                m["benchmarks"][name] = {"source_url": "https://official.example", "revision": "a" * 40,
                    "split": "full", "main_metric": "pass", "task_ids_file": str(ids),
                    "evaluator_commit": "b" * 40, "agent_config_file": str(af),
                    "container_digest": "image@sha256:" + "c" * 64,
                    "command": ["official_runner"], "seeds": [1, 2, 3, 4, 5] if name == "terminal_bench_2" else [42]}
            mf = root / "manifest.json"; write_json(mf, m)
            freeze(mf); self.assertTrue(locked(mf)["frozen"])
            write_json(af, {**agent, "temperature": 0.2})
            with self.assertRaises(ValueError): locked(mf)


if __name__ == "__main__":
    unittest.main()

````

## tests/test_real_template.py

````python
"""Optional CPU integration test using a locally supplied OFFICIAL tokenizer.

QS_TEST_TOKENIZER_DIR=/absolute/local/tokenizer python -m unittest discover -s tests -v
Requires tokenizers and Jinja2; neither downloads files.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwen_swesmith.encoding import encode, encode_pair
from qwen_swesmith.schema import normalize, TOOLS


class RealTokenizer:
    def __init__(self, directory):
        from tokenizers import Tokenizer
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        p = Path(directory)
        self.tok = Tokenizer.from_file(str(p / "tokenizer.json"))
        cfg = json.loads((p / "tokenizer_config.json").read_text())
        env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
        def error(message): raise ValueError(message)
        env.globals["raise_exception"] = error
        env.filters["tojson"] = lambda value, **kw: json.dumps(value, ensure_ascii=False)
        self.template = env.from_string(cfg["chat_template"])

    def apply_chat_template(self, messages, **kwargs):
        return self.template.render(messages=messages, **kwargs)

    def __call__(self, text, **kwargs):
        e = self.tok.encode(text, add_special_tokens=False)
        return {"input_ids": e.ids, "offset_mapping": e.offsets}


@unittest.skipUnless(os.environ.get("QS_TEST_TOKENIZER_DIR"), "Set local official tokenizer path for integration tests")
class OfficialTemplateTests(unittest.TestCase):
    def test_tool_format_and_mask_under_both_preservation_modes(self):
        tok = RealTokenizer(os.environ["QS_TEST_TOKENIZER_DIR"])
        raw = [{"role": "system", "content": "Use tools"}, {"role": "user", "content": "USER_SENTINEL"},
               {"role": "assistant", "content": "Inspect code", "tool_calls": [{"id": "a", "function": {"name": "bash", "arguments": '{"command":"ls"}'}}]},
               {"role": "tool", "content": "TOOL_SENTINEL", "tool_call_ids": ["a"]},
               {"role": "assistant", "content": "Fixed"}]
        messages = normalize(raw)
        for preserve in (True, False):
            rendered = tok.apply_chat_template(messages, tools=TOOLS, tokenize=False,
                add_generation_prompt=False, enable_thinking=True, preserve_thinking=preserve)
            self.assertIn("<function=bash>", rendered)
            self.assertIn("<parameter=command>", rendered)
            e = encode(tok, messages, tools=TOOLS, thinking=True, preserve_thinking=preserve)
            offsets = tok(rendered)["offset_mapping"]
            for sentinel in ("USER_SENTINEL", "TOOL_SENTINEL"):
                begin = rendered.index(sentinel); end = begin + len(sentinel)
                targeted = [e["labels"][i] for i, (s, t) in enumerate(offsets) if s < end and t > begin]
                self.assertTrue(targeted)
                self.assertTrue(all(v == -100 for v in targeted))
            self.assertTrue(any(v != -100 for v in e["labels"]))

    def test_complete_dpo_pair_overlength_is_rejected(self):
        tok = RealTokenizer(os.environ["QS_TEST_TOKENIZER_DIR"])
        pair = {"prompt": [{"role": "user", "content": "Fix code"}], "chosen": "hello", "rejected": "wrong"}
        result = encode_pair(tok, pair, {"max_length": 100, "preserve_thinking": True})
        self.assertTrue(result["chosen"]["input_ids"])
        with self.assertRaises(ValueError):
            encode_pair(tok, pair, {"max_length": 2, "preserve_thinking": True})


if __name__ == "__main__": unittest.main()

````
