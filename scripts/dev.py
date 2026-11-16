import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "apps/api/src")
sys.path.insert(0, env["PYTHONPATH"])
from explainer.config import get_settings
settings = get_settings()
print("\nExplainer Studio · http://127.0.0.1:5173", flush=True)
print("Local access key:", settings.api_token, flush=True)
print("Do not expose this development server to the public internet.\n", flush=True)
commands = [[sys.executable, "-m", "uvicorn", "explainer.api:app", "--host", "127.0.0.1", "--port", "8000"],
            [sys.executable, "-m", "explainer.temporal_worker" if settings.scheduler == "temporal" else "explainer.worker"],
            ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"]]
processes = []
try:
    for command in commands:
        processes.append(subprocess.Popen(command, cwd=ROOT, env=env))
    while all(p.poll() is None for p in processes):
        time.sleep(1)
    raise SystemExit("A service exited; inspect the logs above.")
except KeyboardInterrupt:
    pass
finally:
    for p in processes:
        if p.poll() is None:
            p.terminate()
    for p in processes:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

