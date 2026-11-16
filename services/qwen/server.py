"""HTTP gateway -> persistent, kernel-network-isolated Qwen inference subprocess."""

import atexit
import base64
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="Network-isolated Qwen3-TTS adapter")
lock = threading.Lock()
worker = None
messages = None
ready = False


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=1600)
    language: str = "zh-CN"


def stop():
    global worker, ready
    if worker and worker.poll() is None:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
    worker = None
    ready = False


atexit.register(stop)


def start():
    global worker, messages, ready
    if worker and worker.poll() is None and ready:
        return
    stop()
    here = Path(__file__).resolve().parent
    for name in ["QWEN_BASE_MODEL", "QWEN_REFERENCE_WAV", "QWEN_REFERENCE_TEXT"]:
        if not os.getenv(name):
            raise RuntimeError("Local model and reference configuration required")
    env = os.environ.copy()
    env.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
        GRADIO_ANALYTICS_ENABLED="False",
        TOKENIZERS_PARALLELISM="false",
    )
    worker = subprocess.Popen(
        [sys.executable, str(here / "offline_run.py"), str(here / "infer_worker.py")],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
        close_fds=True,
    )
    messages = queue.Queue(maxsize=4)

    def read(proc, channel):
        for line in proc.stdout:
            if line.startswith("@@READY@@") or line.startswith("@@RESULT@@"):
                channel.put(line)
        channel.put("@@EXIT@@")

    threading.Thread(target=read, args=(worker, messages), daemon=True).start()
    if not messages.get(timeout=300).startswith("@@READY@@"):
        stop()
        raise RuntimeError("Isolated model worker did not start")
    ready = True


@app.get("/health")
def health():
    return {
        "status": "ok",
        "loaded": ready,
        "network_isolation": "kernel-seccomp-required",
    }


@app.post("/synthesize")
def synthesize(body: Speech, authorization: str = Header(default="")):
    key = os.getenv("QWEN_SERVICE_KEY", "")
    if len(key) < 24 or not secrets.compare_digest(authorization, "Bearer " + key):
        raise HTTPException(401, "Valid service key required")
    if body.language not in {"zh-CN", "en-US"}:
        raise HTTPException(422, "Unsupported language")
    with lock:
        try:
            start()
            worker.stdin.write(json.dumps(body.model_dump(), ensure_ascii=False) + "\n")
            worker.stdin.flush()
            line = messages.get(timeout=300)
            if not line.startswith("@@RESULT@@"):
                raise RuntimeError("Worker exited")
            result = json.loads(line[len("@@RESULT@@") :])
            if "error" in result:
                raise RuntimeError(result["error"])
            blob = base64.b64decode(result["audio"], validate=True)
            if len(blob) > 40 * 1024 * 1024:
                raise ValueError("Audio too large")
        except Exception:
            stop()
            raise HTTPException(
                503, "Isolated local inference failed; inspect service logs"
            )
    return Response(blob, media_type="audio/wav")
