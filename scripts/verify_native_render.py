"""Render an authored native-output protocol fixture; not a real Agent inference test."""

import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.api import insert_revision
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief
from explainer.adapters.native_contract import validate_design
from explainer.storage import Storage
from explainer.worker import run_once

output = ROOT / ".verify-native-render"
settings = Settings(
    data_dir=output / "data",
    api_token="native-fixture-only-api-key-123456",
    chrome_executable=os.environ.get("CHROME_EXECUTABLE", ""),
).prepare()
db = Database(settings.data_dir)
project = "native-" + str(time.time_ns())
db.execute(
    "INSERT INTO projects VALUES(?,?,?,?)",
    (project, "local", "Native protocol rendering", time.time()),
)
brief = Brief(
    title="Native Agent protocol fixture",
    prompt="Explain content to video",
    voice="none",
    target_seconds=20,
    duration_mode="exact",
    agent_engine="codex",
)
fixture = json.loads((ROOT / "examples/native-agent-design.json").read_text())


def protocol_fixture(content, brief, *args):
    return validate_design(fixture, content, brief), {
        "provider": brief.agent_engine,
        "authored_fixture": True,
        "actual_inference": False,
    }


with patch("explainer.services.pipeline.native_plan", protocol_fixture):
    revision = insert_revision(db, settings, "local", project, brief)
    run_once(settings, db, job_id=revision["job_id"])
job = db.one("SELECT * FROM jobs WHERE id=?", (revision["job_id"],))
assert job["state"] == "SUCCEEDED", job
store = Storage(settings, db)
deliverables = output / "deliverables"
deliverables.mkdir(exist_ok=True)
for item in db.all(
    "SELECT * FROM outputs WHERE revision_id=?", (revision["revision_id"],)
):
    asset, path = store.get("local", item["asset_id"])
    (deliverables / asset["filename"]).write_bytes(path.read_bytes())
quality = json.loads((deliverables / "quality.json").read_text())
assert quality["media"]["frames"] == 600 and quality["media"]["decode"] == "passed"
report = {
    "result": "passed",
    "authored_protocol_fixture": True,
    "actual_native_inference": False,
    "diagram_rendered": True,
    "editable_export": True,
    "exact_frames": 600,
    "full_decode": True,
}
(output / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
