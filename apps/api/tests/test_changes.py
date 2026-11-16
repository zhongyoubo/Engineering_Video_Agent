import io
import json
import zipfile

import pytest

from explainer.domain import Brief
from explainer.services.changes import apply_instruction
from explainer.services.ingestion import analyze
from explainer.services.planning import plan, template_plan


def test_local_instruction_and_locks(settings):
    brief = Brief(title="Concept", prompt="A useful concept")
    board = template_plan(analyze(brief), brief)
    changed = apply_instruction(board, "标题改为清晰的接口", board.scenes[0].id, settings)
    assert changed.scenes[0].title == "清晰的接口"
    assert board.scenes[0].title == "Concept"
    assert changed.scenes[1:] == board.scenes[1:]
    changed.scenes[0].locked = True
    with pytest.raises(ValueError):
        apply_instruction(changed, "旁白改为测试", changed.scenes[0].id, settings)


def test_unknown_instruction_does_not_fake_success(settings):
    brief = Brief(title="x", prompt="x")
    board = template_plan(analyze(brief), brief)
    with pytest.raises(ValueError):
        apply_instruction(board, "Make everything more impressive", board.scenes[0].id, settings)


def test_llm_unknown_evidence_falls_back(settings, monkeypatch):
    import httpx

    settings.model_url = "http://model.test/v1"
    settings.model_name = "test-model"
    settings.allow_external_model = True
    brief = Brief(title="Concept", prompt="Explain a concept")
    content = analyze(brief)
    invalid = template_plan(content, brief).model_dump()
    invalid["scenes"][0]["claim_ids"] = ["invented-claim"]
    original = httpx.Client
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(invalid)}}]})
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=transport))
    result = plan(content, brief, settings)
    assert any("降级" in note for note in result.notices)
    assert result.scenes[0].claim_ids == ["c_prompt"]


def test_import_rejects_fabricated_media(client, headers):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Import"}).json()["id"]
    brief = Brief(title="Example", prompt="Example")
    content = analyze(brief)
    board = template_plan(content, brief)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("project.json", board.model_dump_json())
        z.writestr("content.json", content.model_dump_json())
        z.writestr(
            "manifest.json",
            json.dumps({"fake": {"path": "media/fake.png", "sha256": "bad", "mime": "image/png"}}),
        )
        z.writestr("media/fake.png", b"not an image")
    response = client.post(
        f"/api/v1/projects/{project}/import",
        headers=headers,
        files={"file": ("project.zip", out.getvalue(), "application/zip")},
    )
    assert response.status_code == 422


def test_import_valid_storyboard(client, headers):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Import"}).json()["id"]
    brief = Brief(title="Imported", prompt="Example")
    content = analyze(brief)
    board = template_plan(content, brief)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("project.json", board.model_dump_json())
        z.writestr("content.json", content.model_dump_json())
        z.writestr("manifest.json", "{}")
    response = client.post(
        f"/api/v1/projects/{project}/import",
        headers=headers,
        files={"file": ("project.zip", out.getvalue(), "application/zip")},
    )
    assert response.status_code == 202
