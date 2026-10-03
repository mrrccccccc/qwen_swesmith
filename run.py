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
