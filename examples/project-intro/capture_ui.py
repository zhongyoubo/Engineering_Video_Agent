"""Capture real local UI actions in one process/network namespace. No model calls."""

import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
out = ROOT / ".verify-project-intro"
out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(
    EXPLAINER_DATA_DIR=str(out / "app-data"),
    EXPLAINER_API_TOKEN="intro-demo-only-not-production-123456",
    EXPLAINER_ENABLE_SANDBOX="false",
)
with (out / "app.log").open("w") as log:
    server = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "scripts/dev.py"],
        env=env,
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    try:
        for attempt in range(80):
            try:
                urllib.request.urlopen("http://127.0.0.1:5173/", timeout=1)
                break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError(
                        "Server exited; inspect .verify-project-intro/app.log"
                    )
                time.sleep(0.25)
        else:
            raise RuntimeError("Timed out waiting for local UI")
        subprocess.run(
            ["node", "examples/project-intro/capture-ui.mjs"], env=env, check=True
        )
    finally:
        if server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            server.wait(timeout=20)
