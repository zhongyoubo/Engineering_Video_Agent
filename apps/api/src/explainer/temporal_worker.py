"""Per-stage durable Temporal orchestration over shared PostgreSQL/S3 or local repositories."""

import asyncio
import json
import logging
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker


@workflow.defn
class VideoWorkflow:
    @workflow.run
    async def run(self, job_id: str):
        result = {}
        for stage in [
            "understanding",
            "planning",
            "runtime",
            "voice",
            "timeline",
            "render",
            "quality",
            "export",
            "finalize",
        ]:
            result = await workflow.execute_activity(
                "video_stage",
                {"job_id": job_id, "stage": stage},
                start_to_close_timeout=timedelta(minutes=45),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=4),
            )
            if result["state"] in {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELED"}:
                return result
            if stage == "planning" and result.get("mode") == "storyboard":
                return await workflow.execute_activity(
                    "video_stage",
                    {"job_id": job_id, "stage": "finalize"},
                    start_to_close_timeout=timedelta(minutes=2),
                    heartbeat_timeout=timedelta(seconds=30),
                )
        return result


@activity.defn(name="video_stage")
async def video_stage(command: dict):
    from .config import get_settings
    from .db import Database, uid
    from .services.pipeline import Pipeline

    settings = get_settings()
    db = Database(settings.data_dir, settings.database_url)
    job_id = command["job_id"]
    while True:
        activity.heartbeat(command)
        current = db.one("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not current:
            raise ValueError("Unknown job")
        revision = db.one("SELECT brief FROM revisions WHERE id=?", (current["revision_id"],))
        mode = json.loads(revision["brief"])["mode"]
        if current["state"] in {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELED"}:
            return {"state": current["state"], "mode": mode}
        job = db.claim(uid("temporal"), settings.lease_seconds, job_id)
        if not job:
            await asyncio.sleep(2)
            continue
        pipeline = Pipeline(
            settings, db, job, until_stage=None if command["stage"] == "finalize" else command["stage"]
        )
        task = asyncio.create_task(asyncio.to_thread(pipeline.run))
        try:
            while not task.done():
                activity.heartbeat(command)
                await asyncio.sleep(2)
            await task
        except asyncio.CancelledError:
            db.execute("UPDATE jobs SET state='CANCEL_REQUESTED' WHERE id=? AND state='RUNNING'", (job_id,))
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=25)
            except (Exception, asyncio.CancelledError):
                pass
            raise
        except Exception:
            logging.exception("Stage %s failed for job %s", command["stage"], job_id)
        return {"state": db.one("SELECT state FROM jobs WHERE id=?", (job_id,))["state"], "mode": mode}


async def dispatch(settings, job_id):
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    try:
        await client.start_workflow(
            VideoWorkflow.run,
            job_id,
            id="video-" + job_id,
            task_queue=settings.temporal_queue,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
    except WorkflowAlreadyStartedError:
        return  # idempotent API retry must not fail a committed job


async def main():
    from .config import get_settings

    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    logging.basicConfig(level=logging.INFO)
    async with Worker(
        client, task_queue=settings.temporal_queue, workflows=[VideoWorkflow], activities=[video_stage]
    ):
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
