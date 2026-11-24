import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "apps/api/src")
env.setdefault("PYTHONUTF8", "1")
sys.path.insert(0, env["PYTHONPATH"])
from explainer.config import get_settings
settings = get_settings()
studio_port = int(env.get("EXPLAINER_DEV_PORT", "5173"))
api_port = int(env.get("EXPLAINER_DEV_API_PORT", "8000"))
print(f"\nExplainer Studio · http://127.0.0.1:{studio_port}", flush=True)
print("Local access key:", settings.api_token, flush=True)
print("Do not expose this development server to the public internet.\n", flush=True)
commands = [[sys.executable, "-m", "uvicorn", "explainer.api:app", "--host", "127.0.0.1", "--port", str(api_port)],
            [sys.executable, "-m", "explainer.temporal_worker" if settings.scheduler == "temporal" else "explainer.worker"],
            ["node", "node_modules/vite/bin/vite.js", "--config", "apps/studio/vite.config.ts", "--strictPort"]]
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

