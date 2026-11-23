"""Contracts and protocol fakes; no model inference or arbitrary authored source execution."""

import json
import zipfile
import pytest
from explainer.domain import Scene, Brief
from explainer.creative_scene import CreativeScene, creative_expectations
from explainer.services.motion import compile_motion, measured_event_budgets
from explainer.services.assets.usage import asset_usage
from explainer.services.creative import source_manifest
from explainer.services.engineering.workspace import Workspace, EngineeringError, source_path
from explainer.services.engineering.contracts import SourceEdit, EngineeringAction
from explainer.services.engineering.controller import EngineeringController
from explainer.services.timeline import TimelineConflict


def design():
    return dict(
        visual_goal="让观众通过翻开书本、抽出书页理解信息如何被取用",
        composition="书本占据左侧主体，右侧保留书页运动与解释的空间",
        palette=["#efb85d", "#305a67", "#f5eedb"],
        techniques=["svg"],
        scene_source="src/scenes/Library.tsx",
        elements=[
            dict(
                id="book",
                role="subject",
                description="有书脊、厚度、封面和分层纸页的可识别立体书本",
                implementation="source",
                source_file="src/assets/Book.tsx",
            )
        ],
        events=[
            dict(
                id="open",
                target="book",
                anchor=dict(phrase="打开书本"),
                duration_ms=1000,
                before="书本封面保持合拢",
                change="封面转开并显露内部纸页",
                after="展开的纸页保持可见",
            )
        ],
    )


def scene():
    return Scene(
        id="library",
        type="cards",
        title="查找资料",
        narration="打开书本取出资料",
        frames=120,
        creation=design(),
    )


def work(tmp_path):
    s = scene()
    compile_motion(s, [dict(text=s.narration, start=0.5, end=1.5)], 30)
    media = tmp_path / "media"
    media.mkdir()
    (media / "noto.otf").write_bytes(b"protocol-only-font")
    w = Workspace(tmp_path / "work")
    w.prepare(dict(scenes=[s.model_dump()], total_frames=s.frames), media)
    return w


@pytest.mark.parametrize(
    "path",
    ["../a.tsx", "/src/a.tsx", "src//a.tsx", "src/../a.tsx", "src/x.py", "src/.hidden/a.tsx", "src/a.tsx?x"],
)
def test_source_asset_paths_are_bounded(path):
    d = design()
    d["elements"][0]["source_file"] = path
    with pytest.raises(ValueError, match="canonical"):
        CreativeScene.model_validate(d)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["events"][0].update(target="missing"),
        lambda d: d["events"][0].update(depends_on=["open"]),
        lambda d: d["palette"].append("javascript:alert(1)"),
        lambda d: d["elements"][0].update(asset_key="surprise"),
        lambda d: d["elements"][0].update(role="camera"),
    ],
)
def test_invalid_creative_plan_cannot_enter_rendering(change):
    d = design()
    change(d)
    with pytest.raises(ValueError):
        CreativeScene.model_validate(d)


def test_motion_uses_real_words_and_retains_the_result():
    s = scene()
    compile_motion(s, [dict(text="打开书本", start=0.5, end=1), dict(text="取出资料", start=1, end=2)], 30)
    e = s.compiled_creative_events[0]
    assert (e.start_frame, e.end_frame, e.timing_source) == (15, 45, "measured_words")
    assert e.before == "书本封面保持合拢" and e.after == "展开的纸页保持可见"
    assert e.end_frame < s.frames
    from explainer.domain import StoryboardIR

    board = StoryboardIR(title="书本", language="zh-CN", audience="general", scenes=[s])
    assert measured_event_budgets(board, {s.id: {"words": [dict(text=s.narration, start=0.5, end=1.5)]}}) == {
        s.id: 46
    }
    s.frames = 45
    with pytest.raises(TimelineConflict):
        compile_motion(s, [dict(text=s.narration, start=0.5, end=1.5)], 30)
    assert s.compiled_creative_events == []


def test_free_motion_channels_can_coexist_but_conflicting_changes_fail():
    s = scene()
    e = s.creation.events[0].model_copy(update={"id": "turn", "channel": "rotation"})
    s.creation.events.append(e)
    compile_motion(s, [dict(text=s.narration, start=0, end=1)], 30)
    assert len(s.compiled_creative_events) == 2
    s.creation.events[1].channel = "state"
    with pytest.raises(TimelineConflict, match="Overlapping"):
        compile_motion(s, [dict(text=s.narration, start=0, end=1)], 30)
    assert not s.compiled_creative_events


def test_custom_images_are_consumed_without_a_semantic_scene():
    d = design()
    d["elements"][0].update(implementation="asset", source_file=None, asset_key="book-photo")
    s = scene().model_copy(update={"creation": CreativeScene.model_validate(d)})
    uses = asset_usage({"scenes": [s.model_dump()]})
    assert set(uses) == {"library:book-photo"} and uses["library:book-photo"]["kind"] == "creative"


def test_created_source_assets_are_required_versioned_and_exported(tmp_path):
    w = work(tmp_path)
    with pytest.raises(EngineeringError, match="Author the planned"):
        source_manifest(w)
    w.edit(
        [
            SourceEdit(path=p, content="export default function Fixture(){return null}")
            for p in ["src/scenes/Library.tsx", "src/assets/Book.tsx"]
        ]
    )
    first = source_manifest(w)
    assert len(first["source_assets"]) == 2
    w.record("fixture", {})
    restored = Workspace(w.root)
    restored.prepare(json.loads((w.project / "props.json").read_text()), tmp_path / "media")
    assert source_manifest(restored) == first
    archive = tmp_path / "editable.zip"
    restored.export(archive, {})
    with zipfile.ZipFile(archive) as z:
        assert json.loads(z.read("creative-manifest.json")) == first
        assert b"Fixture" in z.read("src/assets/Book.tsx")
    restored.state.update(build_hash=restored.fingerprint(), review_hash=restored.fingerprint())
    restored.edit(
        [SourceEdit(path="src/assets/Book.tsx", content="export default function Changed(){return null}")]
    )
    assert source_manifest(restored)["source_assets"] != first["source_assets"]
    assert restored.state["build_hash"] is None and restored.state["review_hash"] is None


def test_creative_review_is_not_satisfied_by_generic_visual_scores(tmp_path):
    w = work(tmp_path)
    w.edit(
        [
            SourceEdit(path=p, content="export default function Fixture(){return null}")
            for p in ["src/scenes/Library.tsx", "src/assets/Book.tsx"]
        ]
    )
    stamp = w.fingerprint()
    w.state.update(preview_hash=stamp, frames=[{"name": "frame.png", "frame": 0}])
    c = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    review = dict(
        accepted=True, legibility=5, visual_explanation=5, timing=5, issues=[], inspected_frames=["frame.png"]
    )

    def act():
        return EngineeringAction(action="review", summary="protocol fixture", files=[], review=review)

    with pytest.raises(EngineeringError, match="created subject"):
        c.apply(act())
    review.update(
        creation_expectations=sorted(
            creative_expectations(json.loads((w.project / "props.json").read_text()))
        ),
        subject_fidelity=4,
        scene_composition=4,
        creative_motion=4,
    )
    c.apply(act())
    assert w.state["review_hash"] == stamp
    review["creative_motion"] = 3
    with pytest.raises(EngineeringError):
        c.apply(act())
    assert w.state["review_hash"] is None


def test_new_native_plans_require_creation_but_saved_plans_remain_loadable(settings, tmp_path):
    from test_materials_ming import production_plan
    from explainer.services.engineering.agent import NativeEngineeringAgent
    from explainer.services.ingestion import analyze
    from explainer.services.materials import material_library
    from explainer.services.process import Runner
    from explainer.adapters.native_agent import NativeOutputError

    b = Brief(title="Test", prompt="Explain a request lifecycle")
    agent = NativeEngineeringAgent(settings, Runner(), analyze(b), b, {}, tmp_path, lambda _: None)
    p = production_plan()
    p.storyboard.scenes[0].creation = None
    assert agent.prepare_plan(p, material_library()).scenes
    with pytest.raises(NativeOutputError, match="creation plan"):
        agent.prepare_plan(p, material_library(), require_creation=True)
    for name in ["creative-kit.ts", "creative-types.ts"]:
        with pytest.raises(EngineeringError):
            source_path("src/" + name)


def test_new_native_creative_images_must_be_declared_in_the_plan(settings, tmp_path):
    from test_materials_ming import production_plan
    from explainer.services.engineering.agent import NativeEngineeringAgent
    from explainer.services.ingestion import analyze
    from explainer.services.materials import material_library
    from explainer.services.process import Runner
    from explainer.adapters.native_agent import NativeOutputError

    b = Brief(title="Test", prompt="Explain a request lifecycle")
    agent = NativeEngineeringAgent(settings, Runner(), analyze(b), b, {}, tmp_path, lambda _: None)
    p = production_plan()
    p.storyboard.scenes[0].creation.elements[0].implementation = "asset"
    p.storyboard.scenes[0].creation.elements[0].source_file = None
    p.storyboard.scenes[0].creation.elements[0].asset_key = "new-subject-image"
    with pytest.raises(NativeOutputError, match="Declare every creative image"):
        agent.prepare_plan(p, material_library(), require_creation=True)


def test_custom_motion_dependencies_reject_cycles_and_temporal_inversion():
    d = design()
    d["events"].append({**d["events"][0], "id": "extract", "depends_on": ["open"], "channel": "position"})
    d["events"][0]["depends_on"] = ["extract"]
    with pytest.raises(ValueError, match="cycle"):
        CreativeScene.model_validate(d)
    d["events"][0]["depends_on"] = []
    s = scene().model_copy(update={"creation": CreativeScene.model_validate(d)})
    with pytest.raises(TimelineConflict, match="prerequisite"):
        compile_motion(s, [dict(text=s.narration, start=0, end=1)], 30)
    assert not s.compiled_creative_events
