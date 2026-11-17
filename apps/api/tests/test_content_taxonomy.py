"""Purpose/subject/form independence and actual pipeline/review integration."""

import json
import pytest

from explainer.config import ROOT
from explainer.domain import Brief, Scene, StoryboardIR
from explainer.editorial import EditorialBrief, EditorialPlan
from explainer.content_taxonomy import INTENT_PROFILES, planning_guidance
from explainer.services.editorial import (
    prepare_presentation,
    publication_findings,
    require_publishable,
    register_runtime_scene,
    EditorialError,
)
from explainer.services.ingestion import analyze


def sample(intent="advice"):
    payload = json.loads((ROOT / "examples/content-strategies" / f"{intent}.json").read_text())
    brief = Brief.model_validate(payload["brief"])
    board = StoryboardIR(
        title=brief.title, language=brief.language, audience=brief.audience, scenes=payload["scenes"]
    )
    prepare_presentation(board, brief, EditorialPlan.model_validate(payload["editorial"]))
    return brief, board, analyze(brief)


def test_taxonomy_endpoint_auth_and_dimensions_match_contract(client, headers):
    assert client.get("/api/v1/content-taxonomy").status_code == 401
    options = client.get("/api/v1/content-taxonomy", headers=headers).json()
    assert {i["id"] for i in options["intents"]} == {
        "introduction",
        "explanation",
        "analysis",
        "viewpoint",
        "advice",
        "tutorial",
    }
    assert "knowledge" not in {i["id"] for i in options["intents"]}
    assert "knowledge" in {i["id"] for i in options["subjects"]}
    assert client.get("/api/v1/capabilities", headers=headers).json()["content_taxonomy"] == options
    for item in options["intents"]:
        assert item["question"] and item["success_criteria"]
        assert EditorialBrief(intent=item["id"], subject_kind="concept").intent == item["id"]


@pytest.mark.parametrize("intent", list(INTENT_PROFILES))
def test_all_six_authored_strategies_validate_with_distinct_outcomes(intent):
    brief, board, content = sample(intent)
    require_publishable(board, content)
    assert board.editorial.strategy.intent == intent
    assert board.editorial_request == brief.editorial
    assert board.editorial.strategy.success_criteria
    assert not [f for f in publication_findings(board, content) if f["severity"] == "error"]


def test_auto_is_model_resolution_not_keywords_and_legacy_knowledge_migrates():
    brief = Brief(title="API", prompt="建议、教学、教程、介绍、分析、观点，都只是本文中的词")
    assert planning_guidance(brief)["request"]["intent"] == "auto"
    assert set(planning_guidance(brief)["profiles"]) == set(INTENT_PROFILES)
    explicit = Brief(
        title="API", prompt="请介绍一个事物", editorial={"intent": "tutorial", "subject_kind": "concept"}
    )
    assert list(planning_guidance(explicit)["profiles"]) == ["tutorial"]
    legacy = EditorialBrief(intent="knowledge", core_message="一个知识点")
    assert (
        legacy.intent == "auto" and legacy.subject_kind == "knowledge" and legacy.core_message == "一个知识点"
    )
    assert EditorialBrief(intent="knowledge", subject_kind="project").subject_kind == "project"
    with pytest.raises(ValueError):
        EditorialBrief(intent="not-a-purpose")


@pytest.mark.parametrize(
    "fields",
    [
        {"intent": "advice", "secondary_intents": ["advice"]},
        {"secondary_intents": ["analysis", "analysis"]},
        {"secondary_intents": ["analysis", "viewpoint", "tutorial"]},
        {"presentation_forms": ["diagram", "diagram"]},
        {"presentation_forms": ["diagram", "case_study", "comparison", "story", "demonstration"]},
    ],
)
def test_invalid_dimension_combinations_rejected(fields):
    with pytest.raises(ValueError):
        EditorialBrief(**fields)


@pytest.mark.parametrize(
    "dimension,value,code",
    [
        ("intent", "introduction", "INTENT_MISMATCH"),
        ("subject_kind", "product", "SUBJECT_MISMATCH"),
        ("audience_level", "advanced", "AUDIENCE_MISMATCH"),
        ("presentation_forms", ["diagram"], "FORM_MISMATCH"),
        ("secondary_intents", ["analysis"], "SECONDARY_MISMATCH"),
    ],
)
def test_resolved_plan_cannot_override_explicit_choices(dimension, value, code):
    _, board, content = sample()
    setattr(board.editorial.strategy, dimension, value)
    assert any(f["code"] == code for f in publication_findings(board, content))
    with pytest.raises(EditorialError):
        require_publishable(board, content)


def test_tutorial_requires_steps_and_completion_check_beyond_a_label():
    _, board, content = sample("tutorial")
    next(b for b in board.editorial.strategy.outline if b.function == "check").function = "evidence"
    with pytest.raises(EditorialError, match="完成检查"):
        require_publishable(board, content)


def test_outline_covers_actual_scenes_in_order_and_once():
    _, board, content = sample()
    board.editorial.strategy.outline[1].scene_ids.append(board.scenes[0].id)
    with pytest.raises(EditorialError, match="覆盖"):
        require_publishable(board, content)


def test_runtime_insertion_remains_in_strategy_and_is_recovery_idempotent():
    _, board, content = sample("tutorial")
    observed = Scene(
        id="observed_run",
        type="terminal",
        title="实际运行",
        narration="这是测试协议中的观察记录",
        verification="runtime",
    )
    board.scenes.insert(-1, observed)
    register_runtime_scene(board, observed.id)
    register_runtime_scene(board, observed.id)
    require_publishable(board, content)
    assert [id for b in board.editorial.strategy.outline for id in b.scene_ids] == [
        s.id for s in board.scenes
    ]


def test_native_planning_carries_guidance_and_rejects_missing_strategy(settings, tmp_path):
    from explainer.services.engineering.agent import NativeEngineeringAgent
    from explainer.services.engineering.contracts import ProductionPlan
    from explainer.services.process import Runner
    from explainer.adapters.native_contract import DesignedScene

    brief, board, content = sample("tutorial")
    design = {
        "protocol": "1.0",
        "scenes": [{k: s.model_dump()[k] for k in DesignedScene.model_fields} for s in board.scenes],
    }
    plan = ProductionPlan(
        objective="Teach the audience to prepare an API request",
        story_arc=["Prepare", "Do", "Check"],
        art_direction="Use readable examples and request flow diagrams",
        voice_direction="Use clear natural Mandarin narration",
        shots=[
            {
                "scene_id": s.id,
                "visual": "Show the actual purpose of this scene",
                "movement": "Reveal the relevant relationship with narration",
                "assets": [],
            }
            for s in board.scenes
        ],
        storyboard=design,
        editorial=board.editorial,
    )
    agent = NativeEngineeringAgent(settings, Runner(), content, brief, {}, tmp_path, lambda *args: None)
    seen = []

    def call(model, payload):
        seen.append(payload)
        return plan, {"fixture": True}

    agent.call = call
    _, result, _ = agent.plan()
    assert seen[0]["content_guidance"]["request"]["intent"] == "tutorial"
    assert result.editorial.strategy.intent == "tutorial"
    plan.editorial.strategy = None
    with pytest.raises(EditorialError, match="四个|表达目的"):
        agent.plan()


def test_purpose_score_required_and_current_hash_invalidated(tmp_path):
    from explainer.services.engineering.workspace import Workspace, EngineeringError
    from explainer.services.engineering.controller import EngineeringController
    from explainer.services.engineering.contracts import EngineeringAction

    _, board, _ = sample("tutorial")
    media = tmp_path / "media"
    media.mkdir()
    w = Workspace(tmp_path / "work")
    w.prepare(board.model_dump(), media)
    stamp = w.fingerprint()
    w.state.update(
        build_hash=stamp,
        preview_hash=stamp,
        frames=[{"name": "first.png", "frame": 0}, {"name": "cover.png", "kind": "thumbnail", "frame": 0}],
    )
    c = EngineeringController(w, None, None, lambda _: None, lambda *args: None, lambda: None)
    review = dict(
        accepted=True,
        legibility=5,
        visual_explanation=5,
        timing=5,
        content_focus=5,
        cover_promise=5,
        opening_closing=5,
        viewer_presentation=5,
        issues=[],
        inspected_frames=["first.png", "cover.png"],
    )
    c.apply(EngineeringAction(action="review", summary="Purpose fixture", files=[], review=review))
    assert w.state["review_hash"] is None
    review["purpose_fulfillment"] = 5
    c.apply(EngineeringAction(action="review", summary="Purpose fixture", files=[], review=review))
    assert w.state["review_hash"] == stamp
    changed = board.model_dump()
    changed["editorial_request"]["audience_level"] = "advanced"
    w.prepare(changed, media)
    with pytest.raises(EngineeringError):
        c.apply(EngineeringAction(action="finish", summary="Purpose fixture", files=[], review=None))


@pytest.mark.parametrize(
    "change",
    [
        {"secondary_intents": ["analysis"]},
        {"subject_kind": "concept"},
        {"audience_description": "需要自己实现接口的工程师"},
        {"audience_level": "advanced"},
        {"presentation_forms": ["diagram", "case_study"]},
    ],
)
def test_each_dimension_change_replans_and_persists(client, headers, settings, db, change):
    from explainer.worker import run_once

    p = client.post("/api/v1/projects", headers=headers, json={"name": "Content dimensions"}).json()
    r = client.post(
        "/api/v1/videos",
        headers=headers,
        json={
            "project_id": p["id"],
            "brief": {
                "title": "接口",
                "prompt": "约定请求和响应",
                "mode": "storyboard",
                "editorial": {"intent": "advice"},
            },
        },
    ).json()
    run_once(settings, db, job_id=r["job_id"])
    original = client.get("/api/v1/revisions/" + r["revision_id"], headers=headers).json()
    brief = original["brief"]
    brief["editorial"].update(change)
    fork = client.post(
        "/api/v1/revisions/" + original["id"] + "/fork",
        headers=headers,
        json={"expected_version": original["version"], "brief": brief, "auto_render": False},
    ).json()
    assert db.one("SELECT storyboard FROM revisions WHERE id=?", (fork["revision_id"],))["storyboard"] is None
    run_once(settings, db, job_id=fork["job_id"])
    saved = client.get("/api/v1/revisions/" + fork["revision_id"], headers=headers).json()
    for key, value in change.items():
        assert saved["storyboard"]["editorial_request"][key] == value
    assert saved["storyboard"]["editorial"] is None  # No model or fake auto classification.
