"""Opt-in integration check against configured real PostgreSQL and S3 services.
Creates test-prefixed records and objects. Run only on a dedicated acceptance DB/bucket.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database
from explainer.storage import Storage
from explainer.api import insert_revision
from explainer.domain import Brief

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="deployment-verification.json")
args = parser.parse_args()
settings = Settings().prepare()
if not settings.database_url or settings.storage_backend != "s3":
    raise SystemExit(
        "Configure a dedicated PostgreSQL database and S3 acceptance bucket first"
    )
run_id = "acceptance_" + uuid.uuid4().hex
with tempfile.TemporaryDirectory(prefix="explainer-acceptance-") as directory:
    first_settings = settings.model_copy(
        update={"data_dir": Path(directory) / "first"}
    ).prepare()
    second_settings = settings.model_copy(
        update={"data_dir": Path(directory) / "second"}
    ).prepare()
    first = Database(first_settings.data_dir, settings.database_url)
    second = Database(second_settings.data_dir, settings.database_url)
    first.execute(
        "INSERT INTO projects VALUES(?,?,?,?)", (run_id, "local", run_id, time.time())
    )
    revision = insert_revision(
        first,
        first_settings,
        "local",
        run_id,
        Brief(title="Acceptance check", prompt="Deployment check", mode="storyboard"),
    )

    def claim(args):
        database, owner = args
        return database.claim(owner, 90, revision["job_id"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(
            pool.map(claim, [(first, run_id + "_a"), (second, run_id + "_b")])
        )
    assert sum(value is not None for value in claims) == 1, (
        "Duplicate lease under concurrent connections"
    )
    old = next(value for value in claims if value)
    first.execute(
        "UPDATE jobs SET lease_until=? WHERE id=?",
        (time.time() - 10, revision["job_id"]),
    )
    recovered = second.claim(run_id + "_recovered", 90, revision["job_id"])
    assert recovered and recovered["fence"] > old["fence"]
    assert not first.finish(old, "SUCCEEDED"), "Stale worker committed"
    assert second.finish(recovered, "CANCELED")
    store_a = Storage(first_settings, first)
    store_b = Storage(second_settings, second)
    data = ("Deployment check " + run_id).encode()
    asset = store_a.put("local", data, "report", run_id + ".txt", "text/plain")
    _, materialized = store_b.get("local", asset["id"])
    assert materialized.read_bytes() == data
    report = {
        "result": "passed",
        "test_id": run_id,
        "concurrent_native_postgres_claim": True,
        "crash_recovery_fencing": True,
        "independent_s3_download": True,
    }
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
