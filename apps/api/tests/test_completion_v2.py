import copy
import json
import time

import pytest

from explainer.domain import Brief
from explainer.services.ingestion import analyze
from explainer.services.planning import template_plan
from explainer.services.timeline import allocate, required_tempo, TimelineConflict, word_cues
from explainer.adapters.project_plan import project_plan, Action, RequestSpec
from explainer.adapters.alignment import validate_words
from explainer.postgres import placeholders, Row


def board():
    b = Brief(title="Test", prompt="Test")
    result = template_plan(analyze(b), b)
    result.scenes = result.scenes[:3]
    return result


def test_exact_frames_preserve_complete_audio():
    b = board()
    brief = Brief(title="Test", prompt="Test", duration_mode="exact", target_seconds=30)
    audio = [{"scene_id": s.id, "duration": 5, "audio_id": "voice"} for s in b.scenes]
    allocate(b, audio, brief)
    assert b.total_frames == 900
    assert [s.start_frame for s in b.scenes] == [
        0,
        b.scenes[0].frames,
        b.scenes[0].frames + b.scenes[1].frames,
    ]
    assert all(s.frames >= 165 for s in b.scenes)


def test_impossible_duration_never_clips():
    b = board()
    original = copy.deepcopy(b)
    brief = Brief(title="Test", prompt="Test", duration_mode="max", target_seconds=20)
    audio = [{"scene_id": s.id, "duration": 20, "audio_id": "voice"} for s in b.scenes]
    with pytest.raises(TimelineConflict):
        required_tempo(b, audio, brief)
    with pytest.raises(TimelineConflict):
        allocate(b, audio, brief)
    assert b == original


def test_locked_frame_budget():
    b = board()
    b.scenes[0].locked = True
    b.scenes[0].frames = 180
    audio = [{"scene_id": s.id, "duration": 4, "audio_id": "voice"} for s in b.scenes]
    brief = Brief(title="Test", prompt="Test", duration_mode="exact", target_seconds=30)
    allocate(b, audio, brief)
    assert b.scenes[0].frames == 180 and b.total_frames == 900


def test_actual_word_times_group_without_length_estimation():
    words = [{"text": "Hello ", "start": 0.7, "end": 1.1}, {"text": "world.", "start": 1.6, "end": 2.1}]
    validate_words(words, "Hello world.", 2.5)
    cues = word_cues(words, "en-US")
    assert cues[0].start == 0.7 and cues[0].end == 2.1
    with pytest.raises(ValueError):
        validate_words(words, "Invented text", 2.5)


def test_temporal_phase_checkpoint_and_fence(settings, db):
    from explainer.api import insert_revision
    from explainer.services.pipeline import Pipeline

    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("p", "local", "p", time.time()))
    r = insert_revision(db, settings, "local", "p", Brief(title="x", prompt="x", mode="storyboard"))
    first = db.claim("phase-one", 90, r["job_id"])
    Pipeline(settings, db, first, until_stage="understanding").run()
    current = db.one("SELECT * FROM jobs WHERE id=?", (r["job_id"],))
    assert current["state"] == "QUEUED" and current["attempts"] == 0
    second = db.claim("phase-two", 90, r["job_id"])
    assert second["fence"] > first["fence"]
    assert not db.finish(first, "SUCCEEDED")
    Pipeline(settings, db, second).run()
    assert db.one("SELECT state FROM jobs WHERE id=?", (r["job_id"],))["state"] == "SUCCEEDED"


@pytest.mark.parametrize("framework,kind", [("vite", "node-web"), ("next", "node-web")])
def test_node_detection(framework, kind):
    files = {
        "apps/web/package.json": {
            "text": json.dumps({"scripts": {"dev": "vite"}, "devDependencies": {framework: "1"}})
        }
    }
    plan = project_plan({"files": files}, Brief(title="x", input_id="i", runtime="auto"))
    assert plan["kind"] == kind and plan["working_directory"] == "apps/web"
    assert "--offline" in plan["install"] and "--ignore-scripts" in plan["install"]


def test_python_api_and_safe_actions():
    plan = project_plan(
        {"files": {"app.py": {"text": "app=FastAPI()"}}}, Brief(title="x", input_id="i", runtime="auto")
    )
    assert plan["kind"] == "python-api" and plan["requests"][0]["path"] == "/openapi.json"
    with pytest.raises(ValueError):
        Action(kind="evaluate", target="body")
    with pytest.raises(ValueError):
        RequestSpec(path="//evil.example/")
    with pytest.raises(ValueError):
        project_plan(
            {"files": {}}, Brief(title="x", input_id="i", runtime="python-cli", runtime_entry="../bad.py")
        )


def test_bound_postgres_sql_keeps_quoted_question_marks():
    assert (
        placeholders("SELECT '?' AS mark WHERE id=? AND value='100%'")
        == "SELECT '?' AS mark WHERE id=%s AND value='100%%'"
    )
    assert Row({"count": 4})[0] == 4


def test_two_worker_s3_repositories(settings, db, tmp_path):
    import boto3
    from moto import mock_aws
    from explainer.storage import Storage

    with mock_aws():
        settings.storage_backend = "s3"
        settings.s3_access_key = "testing"
        settings.s3_secret_key = "testing"
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="explainer")
        first = Storage(settings, db)
        asset = first.put("local", b"actual-object", "report", "test.txt", "text/plain")
        second_settings = settings.model_copy(update={"data_dir": tmp_path / "second"})
        second = Storage(second_settings, db)
        _, path = second.get("local", asset["id"])
        assert (
            path.read_bytes() == b"actual-object"
            and path != first.root / "local" / asset["hash"][:2] / asset["hash"]
        )
        with pytest.raises(KeyError):
            second.get("other", asset["id"])
