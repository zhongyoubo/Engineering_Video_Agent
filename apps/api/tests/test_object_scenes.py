"""Object/port/action contracts, real timing, ownership-free presets and review gates."""

import json
import pytest
from explainer.config import ROOT
from explainer.domain import Scene, StoryboardIR
from explainer.visual_scene import VisualScene
from explainer.services.motion import compile_motion
from explainer.services.visuals import prepare_visual_assets
from explainer.services.timeline import TimelineConflict
from explainer.services.engineering.workspace import source_path, EngineeringError


def data():
    return dict(
        purpose="Show a cable connection and the resulting picture",
        setting="studio",
        objects=[
            dict(
                id="player",
                kind="console",
                label="播放设备",
                x=100,
                y=200,
                width=200,
                height=300,
                ports=[dict(id="out", side="right")],
            ),
            dict(
                id="screen",
                kind="tv",
                label="电视",
                x=900,
                y=50,
                width=650,
                height=400,
                powered=False,
                ports=[dict(id="in", side="left")],
            ),
        ],
        connections=[
            dict(
                id="cable",
                source="player",
                source_port="out",
                target="screen",
                target_port="in",
                connected=False,
            )
        ],
        events=[
            dict(
                id="plug",
                target="cable",
                action="connect",
                anchor=dict(phrase="连接设备"),
                duration_ms=500,
                sound="connect",
            ),
            dict(
                id="power",
                target="screen",
                action="power_on",
                anchor=dict(phrase="连接设备"),
                duration_ms=500,
            ),
            dict(
                id="flow",
                target="cable",
                action="signal",
                anchor=dict(phrase="播放画面"),
                duration_ms=1500,
                depends_on=["plug"],
            ),
            dict(
                id="play",
                target="screen",
                action="play",
                anchor=dict(phrase="播放画面"),
                duration_ms=500,
                depends_on=["power"],
            ),
            dict(
                id="audio",
                target="screen",
                action="sound",
                anchor=dict(phrase="发出声音"),
                duration_ms=1500,
                sound="notify",
            ),
        ],
        sound_enabled=True,
    )


def scene(**kwargs):
    return Scene(
        id="example",
        type="ui",
        title="连接与播放",
        narration="连接设备之后播放画面并发出声音。",
        frames=300,
        duration=10,
        visual_scene=kwargs.pop("visual_scene", data()),
        **kwargs,
    )


def words():
    return [
        dict(text="连接设备", start=0.2, end=1),
        dict(text="之后", start=1, end=1.4),
        dict(text="播放画面", start=1.5, end=2.5),
        dict(text="并", start=2.6, end=2.8),
        dict(text="发出声音", start=3, end=4),
    ]


@pytest.mark.parametrize(
    "case",
    [
        "bad_object",
        "bad_port",
        "same_endpoint",
        "wrong_target",
        "duplicate_id",
        "cycle",
        "unsafe_sound",
        "out_of_stage",
        "nonfinite",
    ],
)
def test_invalid_visual_scene_rejected(case):
    value = data()
    if case == "bad_object":
        value["connections"][0]["source"] = "missing"
    if case == "bad_port":
        value["connections"][0]["target_port"] = "missing"
    if case == "same_endpoint":
        value["connections"][0].update(target="player", target_port="out")
    if case == "wrong_target":
        value["events"][0]["target"] = "screen"
    if case == "duplicate_id":
        value["objects"][0]["id"] = "cable"
    if case == "cycle":
        value["events"][0]["depends_on"] = ["flow"]
    if case == "unsafe_sound":
        value["events"][0]["sound"] = "../../secret"
    if case == "out_of_stage":
        value["objects"][1]["x"] = 1700
    if case == "nonfinite":
        value["objects"][0]["width"] = float("nan")
    with pytest.raises(ValueError):
        VisualScene.model_validate(value)


def test_new_fields_are_data_only_and_unknown_objects_are_not_mislabeled():
    bad = data()
    bad["objects"][0]["kind"] = "arbitrary-object"
    with pytest.raises(ValueError):
        VisualScene.model_validate(bad)
    bad = data()
    bad["objects"][0]["url"] = "http://internal-service"
    with pytest.raises(ValueError):
        VisualScene.model_validate(bad)
    bad = data()
    bad["objects"][0]["code"] = "process.env"
    with pytest.raises(ValueError):
        VisualScene.model_validate(bad)


def test_scene_rejects_missing_spoken_anchor_before_tts():
    value = data()
    value["events"][0]["anchor"]["phrase"] = "not in narration"
    with pytest.raises(ValueError, match="missing from narration"):
        scene(visual_scene=value)
    with pytest.raises(ValueError, match="not both"):
        scene(
            diagram={
                "nodes": [dict(id="x", label="X", x=0, y=0, detail="", reveal=0, emphasis="none")],
                "edges": [],
            }
        )


def test_measured_phrase_actions_and_persistent_state_timings():
    s = scene()
    compile_motion(s, words(), 30)
    by = {e.id: e for e in s.compiled_object_events}
    assert by["plug"].start_frame == 6 and by["plug"].end_frame == 21
    assert by["play"].start_frame == 45 and by["audio"].start_frame == 90
    assert all(e.timing_source == "measured_words" for e in s.compiled_object_events)
    assert s.compiled_events == []
    loaded = Scene.model_validate_json(s.model_dump_json())
    assert loaded.visual_scene == s.visual_scene and loaded.compiled_object_events == s.compiled_object_events


@pytest.mark.parametrize(
    "failure", ["no_measurement", "dependency", "not_connected", "not_powered", "frame_budget"]
)
def test_causality_and_frame_budget_cannot_be_satisfied_by_filled_fields(failure):
    value = data()
    if failure == "dependency":
        value["events"][2]["anchor"]["phrase"] = "连接设备"
    if failure == "not_connected":
        value["events"][0]["action"] = "highlight"
        value["events"][0]["target"] = "player"
        value["events"][2]["depends_on"] = []
    if failure == "not_powered":
        value["events"][1]["action"] = "highlight"
        value["events"][3]["depends_on"] = []
    if failure == "frame_budget":
        value["events"][-1]["duration_ms"] = 9000
    s = scene(visual_scene=value)
    with pytest.raises(TimelineConflict):
        compile_motion(s, [] if failure == "no_measurement" else words(), 30)
    assert s.compiled_object_events == []


def test_draft_estimation_is_labeled_and_never_claimed_measured():
    s = scene()
    compile_motion(s, [], 30, allow_estimated=True)
    assert {e.timing_source for e in s.compiled_object_events} == {"estimated_draft"}


def test_audio_presets_are_local_original_and_explicitly_enabled(tmp_path):
    s = scene()
    compile_motion(s, words(), 30)
    board = StoryboardIR(title="连接", language="zh-CN", audience="general", scenes=[s])
    assert prepare_visual_assets(board, tmp_path) == ["connect", "notify"]
    assert {p.name for p in tmp_path.iterdir()} == {"scene-sfx-connect.wav", "scene-sfx-notify.wav"}
    for p in tmp_path.iterdir():
        assert p.read_bytes().startswith(b"RIFF")
    s.visual_scene.sound_enabled = False
    elsewhere = tmp_path / "disabled"
    elsewhere.mkdir()
    assert prepare_visual_assets(board, elsewhere) == [] and not list(elsewhere.iterdir())


def test_protected_object_renderer_is_not_agent_editable():
    for path in ["src/scene-objects.tsx", "src/nested/scene-objects.tsx"]:
        with pytest.raises(EngineeringError):
            source_path(path)


def test_catalog_and_capability_report_composable_objects_not_prompt_classification(client, headers):
    c = client.get("/api/v1/capabilities", headers=headers).json()
    assert set(c["visual_scene_toolkit"]["objects"]) == {
        "tv",
        "monitor",
        "laptop",
        "console",
        "player",
        "soundbar",
        "speaker",
        "remote",
        "phone",
        "server",
        "router",
    }
    assert "power_on" in c["visual_scene_toolkit"]["actions"]
    assert {i["id"] for i in c["material_library"]["items"]} >= {
        "object.tv",
        "object.server",
        "visual.object_stage",
        "sound.connect",
    }


def test_authored_hdmi_fixture_expresses_objects_actions_and_real_ports():
    value = json.loads((ROOT / "examples/object-scenes/hdmi.json").read_text())
    all_scenes = [Scene.model_validate(s) for s in value["scenes"]]
    assert len(all_scenes) == 8 and all(s.visual_scene and not s.diagram for s in all_scenes)
    assert {"connect", "signal", "power_on", "play", "sound", "press", "volume"} <= {
        e.action for s in all_scenes for e in s.visual_scene.events
    }
    assert any(e.reverse and e.channel == "audio" for s in all_scenes for e in s.visual_scene.events)


def test_later_power_off_cannot_be_overridden_by_a_historic_power_on():
    value = data()
    value["events"].append(
        dict(id="off", target="screen", action="power_off", anchor=dict(phrase="之后"), duration_ms=300)
    )
    s = scene(visual_scene=value)
    with pytest.raises(TimelineConflict, match="power-on"):
        compile_motion(s, words(), 30)
    assert s.compiled_object_events == []


def test_object_review_requires_object_and_causal_scores_at_current_hash(tmp_path):
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.controller import EngineeringController
    from explainer.services.engineering.contracts import EngineeringAction
    from explainer.services.editorial import prepare_presentation

    s = scene()
    s.role = "opening"
    ending = Scene(id="end", type="summary", title="完成", narration="检查连接结果。", role="closing")
    board = StoryboardIR(title="连接设备", language="zh-CN", audience="general", scenes=[s, ending])
    from explainer.domain import Brief

    prepare_presentation(board, Brief(title=board.title, prompt="检查连接"))
    public = tmp_path / "media"
    public.mkdir()
    workspace = Workspace(tmp_path / "work")
    workspace.prepare(board.model_dump(), public)
    stamp = workspace.fingerprint()
    workspace.state.update(
        build_hash=stamp,
        preview_hash=stamp,
        frames=[dict(name="frame.png", frame=10), dict(name="cover.png", frame=0, kind="thumbnail")],
    )
    c = EngineeringController(workspace, None, None, lambda _: None, lambda *args: None, lambda: None)
    review = dict(
        accepted=True,
        legibility=5,
        visual_explanation=5,
        timing=5,
        issues=[],
        inspected_frames=["frame.png", "cover.png"],
        content_focus=5,
        cover_promise=5,
        opening_closing=5,
        viewer_presentation=5,
    )
    c.apply(EngineeringAction(action="review", summary="Object review fixture", files=[], review=review))
    assert workspace.state["review_hash"] is None
    review.update(object_fidelity=5, causal_motion=5)
    c.apply(EngineeringAction(action="review", summary="Object review fixture", files=[], review=review))
    assert workspace.state["review_hash"] == stamp
    modified = board.model_dump()
    modified["scenes"][0]["visual_scene"]["objects"][0]["color"] = "#334455"
    workspace.prepare(modified, public)
    with pytest.raises(EngineeringError):
        c.apply(EngineeringAction(action="finish", summary="Hash fixture", files=[], review=None))
