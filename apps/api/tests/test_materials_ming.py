"""Catalogue and Ming protocol tests; generated WAV below is a fixture, not inference."""

import io
import json
import math
import struct
import wave

import httpx
import pytest

from explainer.config import ROOT
from explainer.domain import Brief, Scene
from explainer.adapters.voice import synthesize, voice_cache_key, voice_configuration
from explainer.services.materials import material_library, material_source, validate_material_references
from explainer.services.process import Runner
from explainer.services.engineering.agent import NativeEngineeringAgent
from explainer.services.engineering.contracts import ProductionPlan
from explainer.services.ingestion import analyze


def test_material_catalogue_is_authenticated_and_reports_provenance(client, headers):
    assert client.get("/api/v1/material-library").status_code == 401
    r = client.get("/api/v1/material-library", headers=headers)
    assert r.status_code == 200
    library = r.json()
    assert len(library["items"]) == 31 and len(library["revision"]) == 64
    by_id = {x["id"]: x for x in library["items"]}
    assert by_id["visual.parameter_mechanisms"]["symbol"] == "MechanismPanel"
    assert by_id["design.editorial_warm"]["source"].endswith("theme.tsx")
    assert by_id["scene.cover"]["symbol"] == "CoverScene"
    assert by_id["visual.graph"]["readiness"] == "unverified"
    assert all(len(x["source_sha256"]) == 64 and x["provenance"] and x["rights"] for x in library["items"])
    assert (
        client.get("/api/v1/capabilities", headers=headers).json()["material_library"]["revision"]
        == library["revision"]
    )


@pytest.mark.parametrize(
    "path",
    [
        "../.env",
        "/etc/passwd",
        ".env",
        "assets/fonts/../fonts/LICENSE.txt",
        "assets\\fonts\\x",
        "apps/api/src/explainer/config.py",
    ],
)
def test_material_paths_cannot_expose_unapproved_sources(path):
    with pytest.raises(ValueError):
        material_source(path)


def production_plan():
    design = json.loads((ROOT / "examples/native-agent-design.json").read_text())
    opening = {**design["scenes"][0], "id": "opening", "type": "title", "role": "opening"}
    closing = {**design["scenes"][0], "id": "closing", "type": "summary", "role": "closing"}
    design["scenes"] = [opening, *design["scenes"], closing]
    return ProductionPlan(
        editorial={
            "strategy": {
                "intent": "explanation",
                "secondary_intents": [],
                "subject_kind": "concept",
                "audience_description": "People learning request/response",
                "audience_level": "introductory",
                "presentation_forms": ["diagram"],
                "rationale": "Explain the request/response relationship",
                "success_criteria": ["Explain how the request connects systems"],
                "outline": [
                    {
                        "function": "orientation",
                        "purpose": "Ask the audience question",
                        "scene_ids": ["opening"],
                    },
                    {"function": "mechanism", "purpose": "Follow the request", "scene_ids": ["explain"]},
                    {
                        "function": "conclusion",
                        "purpose": "Retain the relationship",
                        "scene_ids": ["closing"],
                    },
                ],
            },
            "audience_question": "How does a request travel?",
            "core_message": "Requests connect software systems",
            "viewer_takeaway": "Follow input and response",
            "hook": "Where does a request go?",
            "supports": [
                {"message": "A request connects systems", "claim_ids": ["c_prompt"], "evidence_ids": []}
            ],
            "closing": "Follow the input and response",
            "cover": {"headline": "Follow a request", "subtitle": "Input to response"},
        },
        objective="Explain an engineering process clearly",
        story_arc=["Start", "Explain"],
        art_direction="Use readable visual diagrams and controlled movement",
        voice_direction="Natural Mandarin male narration with smooth phrasing",
        shots=[
            {
                "scene_id": "opening",
                "visual": "Show the audience question",
                "movement": "Keep the headline visible on frame zero",
                "assets": [],
            },
            {
                "scene_id": "closing",
                "visual": "Show the final takeaway",
                "movement": "Hold the conclusion for reading",
                "assets": [],
            },
            {
                "scene_id": "explain",
                "visual": "Show the source and output relationships",
                "movement": "Reveal the relationship along narration cues",
                "assets": ["library:scene.cover@1.1"],
            },
        ],
        storyboard=design,
    )


def test_native_planning_receives_library_and_rejects_invented_materials(settings, tmp_path):
    brief = Brief(title="Test", prompt="Explain a request lifecycle")
    agent = NativeEngineeringAgent(settings, Runner(), analyze(brief), brief, {}, tmp_path, lambda _: None)
    seen = []

    def call(model, payload, **kwargs):
        seen.append(payload)
        return production_plan(), {"fixture": True}

    agent.call = call
    plan, board, report = agent.plan()
    assert (
        report["fixture"] and report["material_library_revision"] == seen[0]["material_library"]["revision"]
    )
    assert "library:scene.cover@1.1" in plan.shots[2].assets and board.scenes
    library = material_library()
    plan.shots[2].assets = ["library:invented@1.0"]
    with pytest.raises(ValueError, match="Unknown or blocked"):
        validate_material_references(plan, library)
    plan.shots[2].assets = ["library:scene.cover@1.1"]
    next(x for x in library["items"] if x["id"] == "scene.cover")["readiness"] = "blocked"
    with pytest.raises(ValueError, match="blocked"):
        validate_material_references(plan, library)


def test_ming_reference_changes_invalidate_only_ming_voice_cache(settings):
    settings.ming_ref_audio = "voices/approved.wav"
    with pytest.raises(ValueError, match="both configured"):
        voice_configuration("ming", settings)
    settings.ming_ref_text = "This reference is an explicitly labelled test fixture."
    first = voice_cache_key("text", "en-US", "ming", settings)
    other = voice_cache_key("text", "en-US", "edge", settings)
    settings.ming_ref_text += " Changed."
    assert first != voice_cache_key("text", "en-US", "ming", settings)
    assert other == voice_cache_key("text", "en-US", "edge", settings)
    first = voice_cache_key("text", "en-US", "ming", settings)
    settings.ming_seed += 1
    assert first != voice_cache_key("text", "en-US", "ming", settings)
    configuration = voice_configuration("ming", settings)
    assert "reference_digest" in configuration and settings.ming_ref_text not in json.dumps(configuration)


def test_ming_speech_protocol_forwards_reference_and_retains_alignment_boundary(
    settings, tmp_path, monkeypatch
):
    wav = io.BytesIO()
    with wave.open(wav, "wb") as audio:
        audio.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        audio.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i * 0.04))) for i in range(24000)))
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, content=wav.getvalue(), headers={"content-type": "audio/wav"})

    original = httpx.Client
    monkeypatch.setattr(
        "explainer.adapters.voice.httpx.Client",
        lambda **kw: original(transport=httpx.MockTransport(respond), **kw),
    )
    settings.ming_url = "http://ming.invalid"
    settings.ming_ref_audio = "voices/approved.wav"
    settings.ming_ref_text = "Reference fixture only."
    result = synthesize(
        Scene(id="test", type="flow", title="Protocol test", narration="测试配音协议"),
        "zh-CN",
        "ming",
        settings,
        tmp_path,
        Runner(),
    )
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/audio/speech"
    assert (
        body["ref_audio"] == settings.ming_ref_audio
        and body["ref_text"] == settings.ming_ref_text
        and body["seed"] == 123
    )
    assert body["model"] == settings.ming_model and 0.49 < result["duration"] < 0.55
    assert result["words"] == [] and result["alignment_method"] == "estimated_sentence"
    assert (tmp_path / "test.wav").is_file()
