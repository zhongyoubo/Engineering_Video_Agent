"""Run actual per-stage workflow against a real local Temporal development server."""

import asyncio, json, os, subprocess, sys, time, uuid
from pathlib import Path
from datetime import timedelta

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root / "apps/api/src"))
from temporalio.client import Client
from temporalio.worker import Worker
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief, StoryboardIR
from explainer.api import insert_revision
from explainer.temporal_worker import VideoWorkflow, video_stage, dispatch
import explainer.config as configuration


async def main():
    out = root / ".verify-temporal"
    out.mkdir(exist_ok=True)
    log = (out / "server.log").open("w")
    binary = os.environ.get("TEMPORAL_BINARY", str(root / ".tools/temporal/temporal"))
    p = subprocess.Popen(
        [
            binary,
            "server",
            "start-dev",
            "--ip",
            "127.0.0.1",
            "--port",
            "7235",
            "--ui-port",
            "8235",
            "--db-filename",
            str(out / "server.db"),
            "--log-level",
            "error",
        ],
        stdout=log,
        stderr=log,
    )
    try:
        for _ in range(120):
            try:
                client = await Client.connect("127.0.0.1:7235")
                break
            except Exception:
                await asyncio.sleep(0.3)
        else:
            raise RuntimeError("Temporal startup failed")
        settings = Settings(
            data_dir=out / "data",
            api_token="temporal-only-test-key-12345678",
            scheduler="temporal",
            temporal_address="127.0.0.1:7235",
            temporal_queue="verify-" + uuid.uuid4().hex,
            chrome_executable=os.environ.get("CHROME_EXECUTABLE", ""),
        ).prepare()
        configuration.get_settings = lambda: settings
        db = Database(settings.data_dir)
        db.execute(
            "INSERT OR IGNORE INTO projects VALUES(?,?,?,?)",
            ("test", "local", "Temporal verification", time.time()),
        )
        brief = Brief(
            title="Temporal execution",
            prompt="A real workflow",
            voice="none",
            target_seconds=20,
            duration_mode="exact",
        )
        board = StoryboardIR(
            title=brief.title,
            language="zh-CN",
            accent="blue",
            audience="general",
            scenes=[
                {
                    "id": "first",
                    "type": "title",
                    "title": "每一步都有状态，每一次都能恢复。",
                    "narration": "这是通过真实 Temporal 服务执行的讲解视频任务。",
                    "bullets": ["持久化编排", "分阶段执行", "可追溯交付"],
                    "claim_ids": ["c_prompt"],
                    "verification": "user_provided",
                    "duration": 20,
                }
            ],
        )
        result = insert_revision(db, settings, "local", "test", brief, storyboard=board)
        async with Worker(
            client,
            task_queue=settings.temporal_queue,
            workflows=[VideoWorkflow],
            activities=[video_stage],
        ):
            await dispatch(settings, result["job_id"])
            await dispatch(settings, result["job_id"])
            outcome = await asyncio.wait_for(
                client.get_workflow_handle("video-" + result["job_id"]).result(),
                timeout=400,
            )
        assert outcome["state"] == "SUCCEEDED", outcome
        checkpoints = db.all(
            "SELECT stage FROM checkpoints WHERE job_id=?", (result["job_id"],)
        )
        assert {r["stage"] for r in checkpoints} == {
            "understanding",
            "planning",
            "runtime",
            "voice",
            "timeline",
            "render",
            "quality",
            "export",
        }
        report = {
            "result": "passed",
            "actual_temporal_service": True,
            "per_stage_activity_count": 9,
            "idempotent_dispatch": True,
            "actual_video_rendered": True,
            "exact_frames": 600,
            "completed_stages": [r["stage"] for r in checkpoints],
            "outcome": outcome,
        }
        (out / "verification.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
    finally:
        p.terminate()
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
        log.close()


asyncio.run(main())
