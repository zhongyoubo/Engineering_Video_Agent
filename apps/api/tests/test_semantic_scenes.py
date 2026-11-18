import pytest
from explainer.domain import Scene
from explainer.semantic_scene import SemanticScene, AssetRequirement
from explainer.services.motion import compile_motion
from explainer.services.timeline import TimelineConflict
from explainer.services.assets.registry import request_assets, restore_assets
from explainer.services.engineering.workspace import Workspace, source_path, EngineeringError
from explainer.services.engineering.contracts import EngineeringAction
from explainer.services.engineering.controller import EngineeringController


def spec():
    return dict(
        viewer_question="工具失败后，怎样重新查询？",
        entities=[
            dict(
                id="query",
                component="ToolCall",
                title="查询问题",
                state="pending",
                items=[dict(text="search_issues", detail="当前项目")],
            )
        ],
        events=[
            dict(
                id="start",
                target="query",
                action="transition",
                anchor=dict(phrase="开始查询"),
                duration_ms=200,
                from_state="pending",
                to_state="running",
            ),
            dict(
                id="finish",
                target="query",
                action="transition",
                anchor=dict(phrase="收到结果"),
                duration_ms=200,
                from_state="running",
                to_state="succeeded",
                items=[dict(text="当前项目"), dict(text="关键阻塞两项")],
                depends_on=["start"],
            ),
        ],
        expectations=[
            dict(id="started", event_id="start", visible_result="工具显示执行中"),
            dict(id="finished", event_id="finish", visible_result="返回两项具体问题"),
        ],
    )


def scene(data=None):
    return Scene(
        id="s",
        type="ui",
        title="工具查询",
        narration="开始查询，然后收到结果。",
        frames=180,
        duration=6,
        semantic_scene=data or spec(),
    )


def words():
    return [
        dict(text="开始查询", start=0.2, end=1),
        dict(text="然后", start=2, end=2.5),
        dict(text="收到结果", start=4, end=4.8),
    ]


def test_real_semantic_timing_and_late_result():
    s = scene()
    compile_motion(s, words(), 30)
    assert [(e.start_frame, e.end_frame, e.timing_source) for e in s.compiled_semantic_events] == [
        (6, 12, "measured_words"),
        (120, 126, "measured_words"),
    ]
    with pytest.raises(TimelineConflict):
        compile_motion(s, [], 30)
    assert s.compiled_semantic_events == []


@pytest.mark.parametrize(
    "change", ["reference", "cycle", "expectation", "phrase", "binding", "nan", "asset", "observed"]
)
def test_reject_inconsistent_semantics(change):
    d = spec()
    if change == "reference":
        d["events"][0]["target"] = "missing"
    if change == "cycle":
        d["events"][0]["depends_on"] = ["finish"]
    if change == "expectation":
        d["expectations"] = []
    if change == "phrase":
        d["events"][0]["anchor"]["phrase"] = "不存在的旁白"
    if change == "binding":
        d["entities"][0]["bind_to"] = "missing"
    if change == "nan":
        d["entities"][0]["x"] = float("nan")
    if change == "asset":
        d["entities"][0]["component"] = "AssetImage"
    if change == "observed":
        d["entities"][0]["provenance"] = "observed"
    with pytest.raises(ValueError):
        scene(d)


@pytest.mark.parametrize(
    "change", ["wrong_state", "overlap", "dependency", "selection", "overflow", "last_frame"]
)
def test_state_and_content_order_must_be_valid(change):
    d = spec()
    if change == "wrong_state":
        d["events"][1]["from_state"] = "pending"
    if change in {"overlap", "dependency"}:
        d["events"][1]["anchor"] = dict(phrase="开始查询", offset_ms=100)
    if change == "selection":
        d["events"][1].update(action="select", selected=5, from_state=None, to_state=None, items=[])
    if change == "overflow":
        d["events"][1].update(action="append", from_state=None, to_state=None, items=[dict(text="一项")] * 12)
    if change == "last_frame":
        d["events"][1]["duration_ms"] = 2000
    s = scene(d)
    with pytest.raises(TimelineConflict):
        compile_motion(s, words(), 30)
    assert s.compiled_semantic_events == []


def requirement():
    return AssetRequirement(
        id="result",
        purpose="展示返回的两项阻塞",
        title="查询结果",
        items=[
            dict(text="接口未冻结", detail="阻塞集成", active=True),
            dict(text="回归测试失败", detail="需核对恢复时间"),
        ],
    )


def workspace(tmp_path):
    w = Workspace(tmp_path / "w")
    (w.project / "public").mkdir(parents=True)
    (w.project / "props.json").write_text('{"scenes":[]}')
    return w


def test_asset_creation_idempotency_and_recovery(tmp_path):
    w = workspace(tmp_path)
    req = requirement()
    first = request_assets(w, [req], lambda: None)
    digest = w.fingerprint()
    assert first == request_assets(w, [req], lambda: None) and digest == w.fingerprint()
    receipt = w.state["generated_assets"]["result"]
    assert "<svg" in receipt["svg"] and "data:font/woff;base64," in receipt["svg"]
    assert (w.project / "public" / receipt["preview_filename"]).read_bytes().startswith(b"\x89PNG")
    (w.project / "public" / receipt["filename"]).unlink()
    restore_assets(w)
    assert w.fingerprint() == digest
    receipt["filename"] = "../../unsafe.svg"
    with pytest.raises(ValueError):
        restore_assets(w)


def test_asset_service_failure_cancellation_and_atomic_batch(tmp_path):
    w = workspace(tmp_path)
    req = requirement()
    unavailable = req.model_copy(update={"id": "other", "provider": "image_service"})
    with pytest.raises(ValueError):
        request_assets(w, [req, unavailable], lambda: None)
    assert not list((w.project / "public").rglob("*.svg")) and not w.state["generated_assets"]
    calls = []

    def cancel():
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("lost lease")

    with pytest.raises(RuntimeError):
        request_assets(w, [req], cancel)
    assert not w.state["generated_assets"]


def test_asset_bytes_invalidate_gates_and_cross_workspace_isolation(tmp_path):
    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    for k in ["build_hash", "preview_hash", "review_hash"]:
        w.state[k] = w.fingerprint()
    other = Workspace(tmp_path / "other")
    (other.project / "public").mkdir(parents=True)
    (other.project / "props.json").write_text('{"scenes":[]}')
    c = EngineeringController(other, None, None, lambda _: None, lambda *a: None, lambda: None)
    with pytest.raises(EngineeringError):
        c.apply(
            EngineeringAction(
                action="inspect_asset", summary="inspect", files=[], review=None, asset_id="result"
            )
        )
    req = requirement()
    req.title = "更新结果"
    request_assets(w, [req], lambda: None)
    assert all(w.state[k] is None for k in ["build_hash", "preview_hash", "review_hash"])
    assert len(w.state["generated_assets"]) == 1


def test_protected_shared_sources():
    for name in ["semantic-kit.tsx", "semantic-types.ts", "review-plan.ts"]:
        with pytest.raises(EngineeringError):
            source_path("src/" + name)


def test_action_requires_real_asset_payload():
    with pytest.raises(ValueError):
        EngineeringAction(action="request_assets", summary="make", files=[], review=None)
    with pytest.raises(ValueError):
        EngineeringAction(
            action="finish", summary="finish", files=[], review=None, asset_requests=[requirement()]
        )


def test_new_scene_types_remain_data_only_and_legacy_loads():
    assert Scene(id="old", type="cards", title="旧镜头", narration="旧数据保持兼容").semantic_scene is None
    for kind in [
        "PromptInput",
        "Conversation",
        "TokenSequence",
        "ContextWindow",
        "DocumentChunks",
        "RetrievalResults",
        "ModelBoundary",
        "ToolCall",
        "TaskState",
        "EvidenceStack",
        "ApprovalGate",
        "CodeWorkspace",
    ]:
        d = spec()
        d["entities"][0]["component"] = kind
        assert SemanticScene.model_validate(d).entities[0].component == kind


def test_asset_inspection_checks_actual_bytes(tmp_path):
    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    c = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    action = EngineeringAction(
        action="inspect_asset", summary="inspect", files=[], review=None, asset_id="result"
    )
    c.apply(action)
    f = w.project / "public" / w.state["generated_assets"]["result"]["filename"]
    f.write_text("changed")
    with pytest.raises(EngineeringError):
        c.apply(action)


def test_unknown_fields_and_executable_paths_are_rejected():
    d = spec()
    d["entities"][0]["url"] = "https://arbitrary.invalid"
    with pytest.raises(ValueError):
        SemanticScene.model_validate(d)
    with pytest.raises(ValueError):
        AssetRequirement.model_validate({**requirement().model_dump(), "command": "shell"})


def test_review_requires_exact_causal_expectations_and_current_source(tmp_path):
    from explainer.services.engineering.contracts import SourceEdit

    w = workspace(tmp_path)
    (w.project / "props.json").write_text(__import__("json").dumps({"scenes": [scene().model_dump()]}))
    w.state["frames"] = [{"name": "actual-result.png"}]
    w.state["preview_hash"] = w.fingerprint()
    controller = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    review = dict(
        accepted=True,
        legibility=5,
        visual_explanation=5,
        timing=5,
        issues=[],
        inspected_frames=["actual-result.png"],
        semantic_accuracy=5,
        semantic_expectations=["s:started"],
    )

    def apply():
        controller.apply(EngineeringAction(action="review", summary="review", files=[], review=review))

    with pytest.raises(EngineeringError, match="every causal"):
        apply()
    review["semantic_expectations"] = ["s:started", "s:finished"]
    review["semantic_accuracy"] = 3
    with pytest.raises(EngineeringError, match="every causal"):
        apply()
    review["semantic_accuracy"] = 5
    apply()
    assert w.state["review_hash"] == w.fingerprint()
    w.edit([SourceEdit(path="src/Video.tsx", content="// changed source")])
    with pytest.raises(EngineeringError, match="current source"):
        apply()


def test_failed_compilation_clears_all_prior_frame_evidence():
    s = scene()
    compile_motion(s, words(), 30)
    assert s.compiled_semantic_events
    s.semantic_scene.events[1].from_state = "failed"
    with pytest.raises(TimelineConflict):
        compile_motion(s, words(), 30)
    assert not s.compiled_semantic_events and not s.compiled_object_events and not s.compiled_events
