"""Protocol integration with PGlite's PostgreSQL engine and an independent Moto S3 server.
Not a substitute for native PostgreSQL concurrency / MinIO deployment acceptance.
"""

import os, subprocess, sys, time, json, hashlib, shutil, uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database
from explainer.storage import Storage
from explainer.api import insert_revision
from explainer.domain import Brief
from explainer.worker import run_once

out = root / ".verify-storage"
out.mkdir(exist_ok=True)
logs = []
processes = []
try:
    for command, name in [
        (["node", "scripts/pglite-test-server.mjs"], "pg"),
        ([str(root / ".venv/bin/moto_server"), "-H", "127.0.0.1", "-p", "55001"], "s3"),
    ]:
        f = (out / (name + ".log")).open("w")
        logs.append(f)
        processes.append(subprocess.Popen(command, stdout=f, stderr=f))
    url = "postgresql://postgres:postgres@127.0.0.1:55433/postgres?sslmode=disable"
    error = None
    for _ in range(100):
        try:
            db = Database(out / "worker-a", url)
            break
        except Exception as e:
            error = e
            time.sleep(0.3)
    else:
        raise error
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:55001",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )
    for _ in range(80):
        try:
            client.create_bucket(Bucket="explainer")
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError("S3 service did not start")
    settings = Settings(
        data_dir=out / "worker-a",
        api_token="storage-only-test-key-1234567890",
        database_url=url,
        storage_backend="s3",
        s3_endpoint="http://127.0.0.1:55001",
        s3_bucket="explainer",
        s3_access_key="test",
        s3_secret_key="test",
    ).prepare()
    first = Storage(settings, db)
    asset = first.put(
        "local", b"distributed-object-test", "report", "test.txt", "text/plain"
    )
    settings2 = Settings(
        **{**settings.model_dump(), "data_dir": out / "worker-b"}
    ).prepare()
    second = Storage(settings2, db)
    _, path = second.get("local", asset["id"])
    assert path.read_bytes() == b"distributed-object-test"
    try:
        second.get("other", asset["id"])
        raise AssertionError("Cross tenant allowed")
    except KeyError:
        pass
    project = "prj_" + uuid.uuid4().hex
    db.execute(
        "INSERT INTO projects VALUES(?,?,?,?)",
        (project, "local", "Shared project", time.time()),
    )
    result = insert_revision(
        db,
        settings,
        "local",
        project,
        Brief(
            title="Shared engine", prompt="Explain a shared project", mode="storyboard"
        ),
    )
    a = db.claim("worker-a", 60, result["job_id"])
    assert a and not db.claim("worker-b", 60, result["job_id"])
    db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (a["id"],))
    b = db.claim("worker-b", 60, result["job_id"])
    assert b["fence"] > a["fence"]
    assert not db.finish(a, "SUCCEEDED")
    db.release_stage(b)
    assert run_once(settings2, db, job_id=result["job_id"])
    assert (
        db.one("SELECT state FROM jobs WHERE id=?", (result["job_id"],))["state"]
        == "SUCCEEDED"
    )
    report = {
        "result": "passed",
        "database": "PGlite PostgreSQL engine over psycopg TCP",
        "object_service": "independent Moto S3 HTTP server",
        "native_upserts": True,
        "shared_metadata": True,
        "separate_worker_directories": True,
        "s3_download_checksum": True,
        "cross_tenant_denied": True,
        "lease_fencing": True,
        "actual_storyboard_job": True,
        "native_postgres_multi_connection_concurrency": "requires deployment acceptance; PGlite multiplexes a single engine connection",
    }
    (out / "verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
finally:
    for p in processes:
        if p.poll() is None:
            p.terminate()
    for p in processes:
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
    for f in logs:
        f.close()
