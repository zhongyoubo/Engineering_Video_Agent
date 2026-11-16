"""Real end-to-end native CLI acceptance, run on a configured dedicated Worker.
This invokes the selected provider and consumes its configured API quota.
"""

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.api import insert_revision
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief
from explainer.worker import run_once
from explainer.storage import Storage

parser = argparse.ArgumentParser()
parser.add_argument("--provider", choices=["codex", "claude-code"], required=True)
parser.add_argument("--output", default="native-deployment-verification.json")
args = parser.parse_args()
settings = Settings().prepare()
if settings.scheduler != "local":
    raise SystemExit(
        "Use a dedicated local scheduler acceptance environment for this test"
    )
db = Database(settings.data_dir, settings.database_url)
project = "native-acceptance-" + str(time.time_ns())
db.execute(
    "INSERT INTO projects VALUES(?,?,?,?)",
    (project, "local", "Native Agent acceptance", time.time()),
)
brief = Brief(
    title="Explain a request lifecycle",
    prompt="Explain how a client request becomes a response, with a two-node animated diagram.",
    agent_engine=args.provider,
    voice="none",
    mode="storyboard",
    target_seconds=20,
    language="en-US",
)
revision = insert_revision(db, settings, "local", project, brief)
run_once(settings, db, job_id=revision["job_id"])
job = db.one("SELECT * FROM jobs WHERE id=?", (revision["job_id"],))
if job["state"] != "SUCCEEDED":
    raise SystemExit("Native deployment check failed: " + str(job["error"]))
output = db.one(
    "SELECT asset_id FROM outputs WHERE revision_id=? AND role='agent'",
    (revision["revision_id"],),
)
assert output, "Native provenance report missing"
_, report_path = Storage(settings, db).get("local", output["asset_id"])
report = {
    "result": "passed",
    "actual_native_inference": True,
    "provider": args.provider,
    "revision_id": revision["revision_id"],
    "agent": json.loads(report_path.read_text()),
    "video_render_in_this_check": False,
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
