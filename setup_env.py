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
