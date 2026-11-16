"""Prepare a local development environment. Run with Python 3.11+."""
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def run(args):
    print("Preparing:", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], check=True)


if not shutil.which("node") or not shutil.which("npm"):
    raise SystemExit("Install Node.js >=20.19 and npm first.")
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    raise SystemExit("Install FFmpeg (including ffprobe) first. Docker Compose also provides it.")
directory = ROOT / ".venv"
if not directory.exists():
    venv.EnvBuilder(with_pip=True).create(directory)
python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if sys.version_info[:2] == (3,12):
    run([python,"-m","pip","install","-r","requirements.lock"])
    run([python,"-m","pip","install","--no-deps","-e","apps/api"])
else:
    run([python, "-m", "pip", "install", "-e", "apps/api[dev]"])
npm = "npm.cmd" if os.name == "nt" else "npm"
run([npm, "ci", "--no-audit", "--no-fund"])
run([npm, "run", "browser:install"])
print("Ready. Run:", python, "scripts/dev.py")

