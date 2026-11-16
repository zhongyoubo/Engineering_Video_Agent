"""Single-host container entrypoint: API plus one durable worker."""
import os
import subprocess
import sys
import time

if len(os.getenv("EXPLAINER_API_TOKEN", "")) < 24:
    raise SystemExit("Set a unique EXPLAINER_API_TOKEN of at least 24 characters")
mode = "explainer.temporal_worker" if os.getenv("EXPLAINER_SCHEDULER") == "temporal" else "explainer.worker"
processes = [subprocess.Popen([sys.executable, "-m", mode]),
             subprocess.Popen([sys.executable, "-m", "uvicorn", "explainer.api:app", "--host", "0.0.0.0", "--port", "8000"])]
try:
    while all(p.poll() is None for p in processes):
        time.sleep(1)
    raise SystemExit(1)
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

