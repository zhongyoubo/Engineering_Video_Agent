"""Regression coverage for the reference-video audit; no native inference is simulated as real."""

import copy
import pytest
from explainer.domain import Brief, Scene, StoryboardIR
from explainer.semantic_scene import SemanticScene
from explainer.services.engineering.contracts import ProductionPlan, EngineeringAction
from explainer.services.engineering.controller import EngineeringController
from explainer.services.engineering.workspace import EngineeringError, source_path
from explainer.services.assets.usage import asset_usage, validate_generated_consumption
from explainer.services.motion import measured_event_budgets, compile_motion
from explainer.services.timeline import allocate, TimelineConflict
from test_engineering import plan
from test_semantic_scenes import workspace, requirement


def duplicated_plan(different=False):
    data = plan().model_dump()
    scene = copy.deepcopy(data["storyboard"]["scenes"][0])
    scene["id"] = "second"
    data["storyboard"]["scenes"].append(scene)
    shot = copy.deepcopy(data["shots"][0])
    shot["scene_id"] = "second"
    first = requirement().model_dump()
    second = copy.deepcopy(first)
    if different:
        second["title"] = "不同镜头的另一张素材"
    data["shots"][0]["asset_requirements"] = [first]
    shot["asset_requirements"] = [second]
    data["shots"].append(shot)
    return data


def test_conflicting_global_asset_ids_cannot_enter_a_production_plan():
    with pytest.raises(ValueError, match="project-wide"):
        ProductionPlan.model_validate(duplicated_plan(True))
    assert len(ProductionPlan.model_validate(duplicated_plan()).shots) == 2


def test_request_must_match_declared_asset_identity(tmp_path):
    w = workspace(tmp_path)
    c = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    c.planned_assets = {"result": requirement()}
    changed = requirement().model_copy(update={"title": "Unplanned replacement"})
    with pytest.raises(EngineeringError, match="conflicts"):
        c.apply(
            EngineeringAction(
                action="request_assets", summary="Request", files=[], review=None, asset_requests=[changed]
            )
        )
    assert not w.state.get("generated_assets")


def late_scene():
    return Scene(
        id="late",
        type="cards",
        title="动作完成",
        narration="先准备最后完成",
        semantic_scene=dict(
            viewer_question="完成时怎样显示结果？",
            entities=[dict(id="result", component="TaskState", title="完成结果", opacity=0)],
            events=[
                dict(
                    id="show",
                    target="result",
                    action="transform",
                    anchor=dict(phrase="最后完成"),
                    duration_ms=700,
                    opacity=1,
                )
            ],
            expectations=[dict(id="shown", event_id="show", visible_result="最后完成时结果可见")],
        ),
    )


def test_measured_tail_event_reserves_a_held_frame_without_trimming_voice():
    s = late_scene()
    words = [dict(text="先准备", start=0.0, end=2.8), dict(text="最后完成", start=2.8, end=3.0)]
    board = StoryboardIR(title=s.title, language="zh-CN", audience="general", scenes=[s])
    audio = [dict(scene_id=s.id, audio_id="real-timing-fixture", duration=3.0)]
    budgets = measured_event_budgets(board, {s.id: {"words": words}})
    assert budgets == {"late": 106}
    allocate(board, audio, Brief(title=s.title, prompt="检查实际词边界"), budgets)
    compile_motion(board.scenes[0], words, 30)
    assert board.total_frames == 106 and board.scenes[0].compiled_semantic_events[0].end_frame == 105
    assert audio[0]["duration"] == 3.0 and words[-1]["end"] == 3.0
    # Six measured scenes need 636 frames; a strict 20-second limit permits only 600.
    many = board.model_copy(deep=True)
    many.scenes = [board.scenes[0].model_copy(update={"id": f"late_{i}"}) for i in range(6)]
    many_audio = [dict(scene_id=x.id, audio_id="timing-fixture", duration=3.0) for x in many.scenes]
    with pytest.raises(TimelineConflict):
        allocate(
            many,
            many_audio,
            Brief(title=s.title, prompt="严格二十秒", target_seconds=20, duration_mode="max"),
            {x.id: 106 for x in many.scenes},
        )
    board.scenes[0].locked = True
    board.scenes[0].frames = 104
    with pytest.raises(TimelineConflict):
        allocate(board, audio, Brief(title=s.title, prompt="锁定镜头"), budgets)


def test_code_focus_rejects_nonexistent_lines_but_accepts_long_source():
    code = "\n".join(["one()"] * 23 + ["important_fix_must_be_seen()"])
    s = Scene(
        id="code",
        type="code",
        title="代码审查",
        narration="检查最后一行",
        code=code,
        motion=dict(
            purpose="代码检查定位到具体源行",
            pattern="code_scan",
            elements=[dict(id="issue", label="问题")],
            code_focus=[dict(element_id="issue", line=24)],
        ),
    )
    assert s.motion.code_focus[0].line == 24
    data = s.model_dump()
    data["motion"]["code_focus"][0]["line"] = 25
    with pytest.raises(ValueError, match="missing source line"):
        Scene.model_validate(data)


def parameter_scene():
    return dict(
        viewer_question="调整强度会怎样改变分支？",
        parameters=[dict(id="level", initial=0, maximum=1)],
        entities=[dict(id="dial", component="Dial", title="强度", parameter_id="level")],
        events=[
            dict(id="increase", action="parameter", target="level", value=1, anchor=dict(phrase="提高强度"))
        ],
        expectations=[dict(id="expanded", event_id="increase", visible_result="拨盘与分支同步变化")],
    )


def test_shared_parameter_events_compile_and_keep_causal_expectations():
    s = Scene(
        id="mechanism",
        type="cards",
        title="强度变化",
        narration="提高强度",
        frames=120,
        semantic_scene=parameter_scene(),
    )
    compile_motion(s, [dict(text="提高强度", start=0.5, end=1.5)], 30)
    assert s.compiled_semantic_events[0].target == "level" and s.compiled_semantic_events[0].value == 1
    for change in ["missing", "range", "collision"]:
        data = parameter_scene()
        if change == "missing":
            data["entities"][0]["parameter_id"] = "other"
        if change == "range":
            data["events"][0]["value"] = 2
        if change == "collision":
            data["parameters"][0]["id"] = "dial"
        with pytest.raises(ValueError):
            SemanticScene.model_validate(data)


def props_with_assets():
    return dict(
        scenes=[
            dict(
                id="s",
                frames=120,
                semantic_scene=dict(
                    background_asset_key="room", entities=[dict(id="tomato", asset_key="tomato", opacity=0)]
                ),
                compiled_semantic_events=[
                    dict(
                        target="tomato",
                        action="transform",
                        opacity=1,
                        start_frame=20,
                        end_frame=40,
                        timing_source="measured_words",
                    )
                ],
            )
        ]
    )


def test_generated_images_must_be_consumed_reviewed_and_actually_animate_a_cutout():
    receipts = {
        key: dict(
            sha256=("a" if key == "room" else "b") * 64,
            request=dict(provider="image_service", transparent=key == "tomato"),
            has_alpha=key == "tomato",
        )
        for key in ["room", "tomato"]
    }
    props = props_with_assets()
    uses = asset_usage(props)
    review = dict(accepted=True, asset_visibility=4, asset_expectations=list(uses))
    assert validate_generated_consumption(props, receipts, review) == uses
    for change in ["unused", "hidden", "wrong_target", "not_reviewed"]:
        p = copy.deepcopy(props)
        r = copy.deepcopy(review)
        if change == "unused":
            p["scenes"][0]["semantic_scene"] = {"entities": []}
        if change == "hidden":
            p["scenes"][0]["compiled_semantic_events"] = []
        if change == "wrong_target":
            p["scenes"][0]["semantic_scene"]["entities"][0]["opacity"] = 1
            p["scenes"][0]["compiled_semantic_events"][0]["target"] = "unrelated"
        if change == "not_reviewed":
            r["asset_expectations"] = ["s:room"]
        with pytest.raises(ValueError):
            validate_generated_consumption(p, receipts, r)


@pytest.mark.parametrize("name", ["theme.tsx", "code-view.tsx", "mechanism-kit.tsx"])
def test_new_trusted_renderers_cannot_be_overwritten_by_agent_source(name):
    with pytest.raises(EngineeringError):
        source_path("src/" + name)


def test_flow_rates_change_stock_without_permitting_silent_stock_resets():
    data = dict(
        viewer_question="处理速度如何影响积压？",
        parameters=[
            dict(id="stock", initial=5, maximum=100),
            dict(id="in", initial=10, maximum=100),
            dict(id="out", initial=2, maximum=100),
        ],
        entities=[
            dict(
                id="queue",
                component="QueueFlow",
                title="等待队列",
                parameter_id="stock",
                inflow_id="in",
                outflow_id="out",
            )
        ],
        events=[
            dict(id="faster", action="parameter", target="out", value=20, anchor=dict(phrase="加快处理"))
        ],
        expectations=[dict(id="drain", event_id="faster", visible_result="处理能力提高后等待量下降")],
    )
    assert SemanticScene.model_validate(data).entities[0].outflow_id == "out"
    data["events"][0]["target"] = "stock"
    with pytest.raises(ValueError, match="integrated"):
        SemanticScene.model_validate(data)


def test_asset_review_cannot_accept_receipts_without_visible_binding_evidence(tmp_path):
    from test_engineering import accepted_review
    import json

    w = workspace(tmp_path)
    (w.project / "props.json").write_text(json.dumps(props_with_assets()))
    stamp = w.fingerprint()
    w.state.update(preview_hash=stamp, build_hash=stamp, frames=[dict(name="frame.png", frame=30)])
    controller = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    review = accepted_review()
    with pytest.raises(EngineeringError, match="material binding"):
        controller.apply(EngineeringAction(action="review", summary="Observe", files=[], review=review))
    review.update(asset_visibility=5, asset_expectations=["s:room", "s:tomato"])
    controller.apply(
        EngineeringAction(action="review", summary="Observe all materials", files=[], review=review)
    )
    assert w.state["review_hash"] == stamp


def test_build_rejects_recovered_asset_that_no_longer_matches_plan(tmp_path):
    from explainer.services.assets.registry import request_assets
    import json

    w = workspace(tmp_path)
    old = requirement()
    request_assets(w, [old], lambda: None)
    props = json.loads((w.project / "props.json").read_text())
    props["scenes"] = [
        dict(id="s", frames=120, semantic_scene=dict(background_asset_key=old.id, entities=[]))
    ]
    (w.project / "props.json").write_text(json.dumps(props))
    c = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    c.planned_assets = {old.id: old.model_copy(update={"title": "新版素材要求"})}
    with pytest.raises(EngineeringError, match="stale"):
        c.apply(EngineeringAction(action="build", summary="Compile", files=[], review=None))
    c.planned_assets = {old.id: old}
    receipt = w.state["generated_assets"][old.id]
    (w.project / "public" / receipt["filename"]).write_bytes(b"corrupt")
    with pytest.raises(EngineeringError, match="bytes"):
        c.apply(EngineeringAction(action="build", summary="Compile", files=[], review=None))
