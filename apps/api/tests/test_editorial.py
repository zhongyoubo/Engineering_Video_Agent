"""Creator policy and revision gates. Fixtures do not simulate model quality certification."""

import json
import pytest

from explainer.domain import Brief, Scene, StoryboardIR
from explainer.editorial import EditorialPlan, ViewerDisclosure
from explainer.services.editorial import (
    prepare_presentation,
    publication_findings,
    require_publishable,
    EditorialError,
)
from explainer.services.ingestion import analyze
from explainer.services.planning import template_plan
from explainer.services.engineering.workspace import EngineeringError, source_path
from explainer.services.engineering.controller import EngineeringController
from explainer.services.engineering.contracts import EngineeringAction


def creator(title="Ming TTS"):
    brief = Brief(title=title, prompt="用自己的稿件检查音色和表达")
    board = StoryboardIR(
        title=title,
        language="zh-CN",
        audience="general",
        scenes=[
            Scene(id="opening", type="title", title=title, narration="如何选择合适的配音？"),
            Scene(
                id="example",
                type="code",
                title="调用示意",
                narration="固定文稿进行试听",
                disclosures=[{"text": "调用示意"}],
            ),
            Scene(
                id="closing",
                type="summary",
                title="先试听再选择",
                narration="用自己的稿件检查表达",
                message="用自己的稿件检查表达",
            ),
        ],
    )
    prepare_presentation(board, brief)
    return brief, board, analyze(brief)


def test_creator_contract_preserves_evidence_and_local_disclosure():
    brief, board, content = creator()
    assert brief.presentation_profile == "creator" and brief.editorial.intent == "auto"
    assert board.cover.headline == "Ming TTS"
    assert board.scenes[0].role == "opening" and board.scenes[-1].role == "closing"
    assert board.scenes[1].verification == "concept"
    assert board.scenes[1].disclosures[0].text == "调用示意"
    require_publishable(board, content)
    assert any(f["code"] == "EDITORIAL_REVIEW" for f in publication_findings(board, content))
    with pytest.raises(ValueError):
        ViewerDisclosure(text="说明", start_seconds=5, end_seconds=4)


def test_tool_self_credit_blocked_but_project_analysis_allowed():
    _, board, content = creator()
    board.scenes[-1].narration = "本片由工程视频智能体项目的模板兼容模式制作。"
    with pytest.raises(EditorialError, match="自宣传"):
        require_publishable(board, content)
    board.title = "Engineering Video Agent 项目分析"
    require_publishable(board, content)
    board.title = "Ming TTS"
    board.presentation_profile = "engineering_report"
    require_publishable(board, content)


def test_internal_labels_rejected_without_removing_evidence_metadata():
    _, board, content = creator()
    board.scenes[1].disclosures = [ViewerDisclosure(text="概念讲解")]
    with pytest.raises(EditorialError, match="内部验证分类"):
        require_publishable(board, content)
    assert board.scenes[1].verification == "concept"


def test_saved_cover_and_narration_remain_authoritative():
    brief, board, _ = creator()
    board.cover.headline = "先用自己的文稿试听"
    before = [(s.narration, s.frames, s.audio_id, s.cues) for s in board.scenes]
    prepare_presentation(board, brief)
    assert board.cover.headline == "先用自己的文稿试听"
    assert before == [(s.narration, s.frames, s.audio_id, s.cues) for s in board.scenes]


def test_editorial_support_uses_real_evidence_ids():
    _, board, content = creator()
    board.editorial = EditorialPlan(
        audience_question="怎么选择？",
        core_message="先试听",
        viewer_takeaway="准备自己的稿件",
        hook="功能多就一定适合吗？",
        supports=[{"message": "检查表达", "claim_ids": ["invented"]}],
        closing="先试听再选择",
        cover={"headline": "怎么选择？"},
    )
    with pytest.raises(EditorialError, match="不存在"):
        require_publishable(board, content)
    board.editorial.supports[0].claim_ids = ["c_prompt"]
    require_publishable(board, content)


def test_compatibility_draft_does_not_repeat_entire_prompt_or_narrate_production():
    brief = Brief(
        title="测试主题",
        prompt="先选择文稿。再检查表达。最后验证长句",
        editorial={"viewer_takeaway": "用实际文稿判断"},
    )
    board = template_plan(analyze(brief), brief)
    assert [s.narration for s in board.scenes[1:-1]] == ["先选择文稿", "再检查表达", "最后验证长句"]
    assert board.scenes[-1].narration == "用实际文稿判断"
    assert all("编辑器" not in s.narration and "模板" not in s.narration for s in board.scenes)
    assert board.editorial is None and board.notices


def test_publication_presentation_module_is_protected():
    with pytest.raises(EngineeringError):
        source_path("src/presentation.tsx")


def test_creator_review_requires_thumbnail_and_content_scores(tmp_path):
    from explainer.services.engineering.workspace import Workspace

    brief, board, _ = creator()
    media = tmp_path / "media"
    media.mkdir()
    w = Workspace(tmp_path / "work")
    w.prepare(board.model_dump(), media)
    stamp = w.fingerprint()
    w.state.update(build_hash=stamp, preview_hash=stamp, frames=[{"name": "frame.png", "frame": 0}])
    c = EngineeringController(w, None, None, lambda _: None, lambda *args: None, lambda: None)
    review = dict(
        accepted=True, legibility=5, visual_explanation=5, timing=5, issues=[], inspected_frames=["frame.png"]
    )
    with pytest.raises(EngineeringError, match="thumbnail"):
        c.apply(EngineeringAction(action="review", summary="Fixture review", files=[], review=review))
    w.state["frames"].append({"name": "cover.png", "frame": 0, "kind": "thumbnail"})
    review["inspected_frames"].append("cover.png")
    c.apply(EngineeringAction(action="review", summary="Fixture review", files=[], review=review))
    assert w.state["review_hash"] is None
    review.update(content_focus=5, cover_promise=5, opening_closing=5, viewer_presentation=5)
    c.apply(EngineeringAction(action="review", summary="Fixture review", files=[], review=review))
    assert w.state["review_hash"] == stamp
    changed = board.model_dump()
    changed["cover"]["headline"] = "新的封面承诺"
    w.prepare(changed, media)
    with pytest.raises(EngineeringError, match="current source"):
        c.apply(EngineeringAction(action="finish", summary="Fixture finish", files=[], review=None))


def test_self_credit_fails_before_tts(settings, db, monkeypatch):
    import time
    from explainer.api import insert_revision
    from explainer.worker import run_once

    brief, board, content = creator()
    board.scenes[-1].narration = "本片由工程视频智能体项目制作。"
    brief.voice = "edge"
    monkeypatch.setattr(
        "explainer.services.pipeline.synthesize", lambda *args: pytest.fail("Must reject before paid TTS")
    )
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("creator", "local", "Creator", time.time()))
    result = insert_revision(
        db, settings, "local", "creator", brief, storyboard=board, content=json.dumps(content.model_dump())
    )
    run_once(settings, db, job_id=result["job_id"])
    assert "自宣传" in db.one("SELECT error FROM jobs WHERE id=?", (result["job_id"],))["error"]
    assert db.one("SELECT state FROM jobs WHERE id=?", (result["job_id"],))["state"] == "FAILED"
    assert not db.all("SELECT * FROM voice_cache")


def test_changing_content_intent_requires_replanning(client, headers, settings, db):
    from explainer.worker import run_once

    p = client.post("/api/v1/projects", headers=headers, json={"name": "Creator"}).json()
    r = client.post(
        "/api/v1/videos",
        headers=headers,
        json={
            "project_id": p["id"],
            "brief": {"title": "配音选型", "prompt": "先试听", "mode": "storyboard"},
        },
    ).json()
    run_once(settings, db, job_id=r["job_id"])
    original = client.get("/api/v1/revisions/" + r["revision_id"], headers=headers).json()
    changed = original["brief"]
    changed["editorial"]["intent"] = "advice"
    result = client.post(
        "/api/v1/revisions/" + original["id"] + "/fork",
        headers=headers,
        json={"expected_version": original["version"], "brief": changed, "auto_render": False},
    )
    assert result.status_code == 202
    saved = db.one("SELECT * FROM revisions WHERE id=?", (result.json()["revision_id"],))
    assert saved["storyboard"] is None
    assert json.loads(saved["brief"])["editorial"]["intent"] == "advice"
