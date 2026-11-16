"""Real provider -> generated TSX -> isolated rendering acceptance. Consumes API quota."""

import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief
from explainer.api import insert_revision
from explainer.worker import run_once

parser = argparse.ArgumentParser()
parser.add_argument("--provider", choices=["codex", "claude-code"], required=True)
parser.add_argument("--draft", action="store_true")
parser.add_argument("--output", default="engineering-deployment-verification.json")
args = parser.parse_args()
settings = Settings().prepare()
if settings.scheduler != "local":
    raise SystemExit("Use a dedicated local scheduler acceptance environment")
db = Database(settings.data_dir, settings.database_url)
project = "engineering-acceptance-" + str(time.time_ns())
db.execute(
    "INSERT INTO projects VALUES(?,?,?,?)",
    (project, "local", "Engineering acceptance", time.time()),
)
brief = Brief(
    title="从想法到视频工程",
    prompt="用不同的视觉表达，直观解释内容策划、动画工程、配音对齐与渲染验证。",
    target_seconds=30,
    video_mode="engineering",
    agent_engine=args.provider,
    quality_profile="draft" if args.draft else "professional",
    voice="none" if args.draft else "qwen",
)
r = insert_revision(db, settings, "local", project, brief)
run_once(settings, db, job_id=r["job_id"])
job = db.one("SELECT * FROM jobs WHERE id=?", (r["job_id"],))
if job["state"] != "SUCCEEDED":
    raise SystemExit("Engineering acceptance failed: " + str(job["error"]))
roles = {
    x["role"]
    for x in db.all("SELECT role FROM outputs WHERE revision_id=?", (r["revision_id"],))
}
assert {
    "video",
    "engineering_project",
    "visual_review",
    "authoring_journal",
    "production_plan",
} <= roles
report = {
    "result": "passed",
    "actual_native_inference": True,
    "isolated_generated_code": True,
    "provider": args.provider,
    "draft": args.draft,
    "revision_id": r["revision_id"],
    "human_quality_acceptance": False,
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
