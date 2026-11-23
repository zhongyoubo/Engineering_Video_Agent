"""Cross-module regressions from the full project review. Only trusted protocol/stdlib fixtures."""

import io
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import zipfile

import pytest
from explainer.config import Settings
from explainer.db import SQLiteDatabase
from explainer.services.pipeline import Pipeline, Canceled, LostLease
from explainer.services.process import Runner, ProcessError
from explainer.services.ingestion import read_archive, InvalidArchive
from test_queue import seed


def test_asset_range_requests_are_bounded_without_breaking_seeking(client, headers, settings, db):
    from explainer.storage import Storage

    blob = b"0123456789" * 200
    asset = Storage(settings, db).put("local", blob, "fixture", "range.bin", "application/octet-stream")
    url = "/api/v1/assets/" + asset["id"]
    single = client.get(url, headers={**headers, "Range": "bytes=0-15"})
    assert single.status_code == 206 and single.content == blob[:16]
    excessive = "bytes=" + ",".join(f"{i * 2}-{i * 2}" for i in range(101))
    bounded = client.get(url, headers={**headers, "Range": excessive})
    # Starlette deliberately ignores >100 ranges and serves one bounded full response.
    assert bounded.status_code == 200 and bounded.content == blob
    assert "multipart/byteranges" not in bounded.headers.get("content-type", "")


def test_upload_rejects_excessive_multipart_part_headers(client, headers):
    from test_ingestion import archive

    project = client.post("/api/v1/projects", headers=headers, json={"name": "header limits"}).json()["id"]
    zipped = archive({"main.py": "print(1)"})
    body = (
        b'--review-boundary\r\nContent-Disposition: form-data; name="file"; filename="code.zip"\r\n'
        b"Content-Type: application/zip\r\nX-Review: "
        + b"a" * 131072
        + b"\r\n\r\n"
        + zipped
        + b"\r\n--review-boundary--\r\n"
    )
    response = client.post(
        f"/api/v1/projects/{project}/inputs",
        headers={**headers, "Content-Type": "multipart/form-data; boundary=review-boundary"},
        content=body,
    )
    assert response.status_code in {400, 413}


@pytest.mark.parametrize(
    "text, secret",
    [
        ('DATABASE_URL = "postgresql://customer:private-db-pass@db.example/app"', "private-db-pass"),
        (
            "curl -H 'Authorization: Bearer private-access-credential-12345' https://example.test/api",
            "private-access-credential-12345",
        ),
    ],
)
def test_model_source_snapshot_removes_uri_and_authorization_credentials(settings, text, secret):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("README.md", text)
    manifest = read_archive(stream.getvalue(), settings)
    assert secret not in manifest["files"]["README.md"]["text"]
    assert "[REDACTED]" in manifest["files"]["README.md"]["text"]


def test_redaction_keeps_ordinary_reference_urls():
    from explainer.services.ingestion import redact

    text = "See https://example.test/docs?q=api and https://example.test?email=a@b.test. Bearer tokens identify requests."
    assert redact(text) == text


def test_failed_renderer_process_cannot_promote_its_success_receipt(settings, tmp_path, monkeypatch):
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.tools import RenderTools
    from unittest.mock import Mock
    import json

    w = Workspace(tmp_path / "render-work")

    def failed(*args, **kwargs):
        (w.root / "tool-000-build/result.json").write_text(
            json.dumps(dict(protocol="3.0", action="build", ok=True))
        )
        raise ProcessError("Process timeout")

    monkeypatch.setattr("explainer.services.engineering.tools.shutil.which", lambda _: "/fixture/docker")
    monkeypatch.setattr("explainer.services.engineering.tools.subprocess.run", Mock())
    runner = Mock()
    runner.run.side_effect = failed
    assert RenderTools(settings, runner).execute(w, "build")["ok"] is False


def test_local_instruction_preserves_full_legal_narration(settings):
    from test_completion_v2 import board
    from explainer.services.changes import apply_instruction

    current = board()
    text = "完整的讲解内容。" * 240
    result = apply_instruction(current, "旁白改为：" + text, current.scenes[0].id, settings)
    assert result.scenes[0].narration == text
    with pytest.raises(ValueError):
        apply_instruction(current, "标题改为：" + "长" * 100, current.scenes[0].id, settings)


def test_qwen_rejects_oversized_scene_before_starting_http(settings, tmp_path, monkeypatch):
    from unittest.mock import Mock
    from explainer.domain import Scene
    from explainer.adapters.voice import synthesize

    monkeypatch.setattr(
        "explainer.adapters.voice.httpx.Client", Mock(side_effect=AssertionError("HTTP must not start"))
    )
    scene = Scene(id="long", type="cards", title="长旁白", narration="长" * 1601)
    with pytest.raises(ValueError, match="1600"):
        synthesize(scene, "zh-CN", "qwen", settings, tmp_path, Mock())


def create_job(client, headers, project):
    return client.post(
        "/api/v1/videos",
        headers=headers,
        json=dict(
            project_id=project,
            brief=dict(title="Review", prompt="Review protocol", mode="storyboard", voice="none"),
        ),
    ).json()


def test_cancel_racing_with_worker_claim_is_still_observed(client, headers, settings, db, monkeypatch):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "race"}).json()["id"]
    job = create_job(client, headers, project)["job_id"]
    original = SQLiteDatabase.one
    claimed = []

    def racing_read(self, sql, args=()):
        value = original(self, sql, args)
        if sql == "SELECT * FROM jobs WHERE id=? AND tenant=?" and args[0] == job and not claimed:
            claimed.append(self.claim("racing-worker", 90, job))
        return value

    monkeypatch.setattr(SQLiteDatabase, "one", racing_read)
    response = client.post(f"/api/v1/jobs/{job}/cancel", headers=headers)
    assert response.status_code == 200 and response.json()["state"] == "CANCEL_REQUESTED"
    with pytest.raises(Canceled):
        Pipeline(settings, db, claimed[0]).guard()


def test_retry_obeys_the_same_active_quota_as_creation(client, headers, settings, db):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "quota"}).json()["id"]
    failed = create_job(client, headers, project)["job_id"]
    db.execute("UPDATE jobs SET state='FAILED' WHERE id=?", (failed,))
    for _ in range(settings.max_active_jobs):
        assert "job_id" in create_job(client, headers, project)
    response = client.post(f"/api/v1/jobs/{failed}/retry", headers=headers)
    assert response.status_code == 429
    assert db.one("SELECT state FROM jobs WHERE id=?", (failed,))["state"] == "FAILED"


@pytest.mark.parametrize("state", ["CANCELED", "FAILED", "QUEUED", "SUCCEEDED"])
def test_terminal_or_released_worker_cannot_continue(settings, db, state):
    seed(settings, db)
    job = db.claim("worker", 90)
    db.execute("UPDATE jobs SET state=? WHERE id=?", (state, job["id"]))
    with pytest.raises(Canceled if state == "CANCELED" else LostLease):
        Pipeline(settings, db, job).guard()


@pytest.mark.parametrize("method", ["finish", "release_stage"])
def test_expired_worker_cannot_revive_a_swept_failure(settings, db, method):
    seed(settings, db)
    job = db.claim("worker", 90)
    db.execute("UPDATE jobs SET state='FAILED' WHERE id=?", (job["id"],))
    result = db.finish(job, "SUCCEEDED") if method == "finish" else db.release_stage(job)
    assert result is False
    assert db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "FAILED"


def test_stage_rechecks_terminal_state_before_checkpoint_commit(settings, db):
    seed(settings, db)
    job = db.claim("worker", 90)
    p = Pipeline(settings, db, job)

    def invalidated():
        db.execute("UPDATE jobs SET state='FAILED' WHERE id=?", (job["id"],))
        return {"outputs": {}, "value": 1}

    with pytest.raises(LostLease):
        p.stage("review-unit", 0.1, invalidated)
    assert db.one("SELECT * FROM checkpoints WHERE job_id=?", (job["id"],)) is None


@pytest.mark.parametrize("names", [["a", "a/b.py"], ["a/b.py", "a"]])
def test_zip_file_directory_collisions_are_rejected_at_ingestion(settings, names):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name in names:
            z.writestr(name, 'print("trusted test")')
    with pytest.raises(InvalidArchive):
        read_archive(stream.getvalue(), settings)


def test_access_token_creation_handles_check_then_create_race(tmp_path, monkeypatch):
    key = "competing-startup-key-with-enough-entropy"
    token = tmp_path / "access-token"
    token.write_text(key)
    original = Path.exists
    monkeypatch.setattr(Path, "exists", lambda p: False if p == token else original(p))
    assert Settings(data_dir=tmp_path, api_token="").prepare().api_token == key
    assert token.read_text() == key


def test_parallel_first_startups_see_one_complete_token(tmp_path):
    with ThreadPoolExecutor(max_workers=12) as pool:
        keys = list(
            pool.map(lambda _: Settings(data_dir=tmp_path, api_token="").prepare().api_token, range(24))
        )
    assert len(set(keys)) == 1 and len(keys[0]) >= 24


def test_process_deadline_includes_descendants_holding_output_open():
    code = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c","import time; time.sleep(3)"]); print("leader done",flush=True)'
    start = time.monotonic()
    with pytest.raises(ProcessError, match="timeout"):
        Runner().run([sys.executable, "-c", code], timeout=0.3)
    assert time.monotonic() - start < 2


def test_process_cleanup_allows_sigterm_handlers_before_force_kill(tmp_path):
    target = tmp_path / "cleanup.txt"
    code = (
        "import signal,time,sys;from pathlib import Path;"
        f'signal.signal(signal.SIGTERM,lambda *a:(Path({str(target)!r}).write_text("closed"),sys.exit(0)));'
        'print("ready",flush=True);time.sleep(10)'
    )
    with pytest.raises(ProcessError):
        Runner().run([sys.executable, "-c", code], timeout=0.3)
    assert target.read_text() == "closed"


def test_successful_leader_does_not_leave_background_descendants(tmp_path):
    target = tmp_path / "late.txt"
    child = f'import time;from pathlib import Path;time.sleep(.8);Path({str(target)!r}).write_text("late")'
    leader = (
        'import subprocess,sys;subprocess.Popen([sys.executable,"-c",'
        + repr(child)
        + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)"
    )
    Runner().run([sys.executable, "-c", leader], timeout=2)
    time.sleep(1)
    assert not target.exists()
