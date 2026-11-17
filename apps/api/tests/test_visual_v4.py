import json
import math
import struct
import wave

import httpx
import pytest
from PIL import Image, ImageDraw

from explainer.domain import Brief, Scene, StoryboardIR, Cue
from explainer.specs import VoiceSpec, SceneSpec
from explainer.adapters.voice import voice_cache_key, voice_configuration
from explainer.services.motion import compile_motion
from explainer.services.timeline import TimelineConflict
from explainer.services.audio_analysis import waveform
from explainer.services.engineering.tools import inspect_frame
from explainer.services.engineering.workspace import EngineeringError, source_path
from explainer.mcp_server import VideoAPI, safe_id


def scene():
    return Scene(
        id="queue",
        type="flow",
        title="请求与队列",
        narration="请求增加，队列积累。",
        frames=150,
        motion=SceneSpec(
            purpose="解释请求增加与队列的关系",
            pattern="queue",
            elements=[{"id": "queue", "label": "队列"}],
            events=[
                {
                    "id": "grow",
                    "target": "queue",
                    "action": "progress",
                    "anchor": {"phrase": "队列"},
                    "duration_ms": 500,
                }
            ],
        ),
    )


def test_motion_uses_measured_word_boundaries_and_recompiles():
    s = scene()
    words = [
        {"text": "请求增加，", "start": 0.2, "end": 1.2},
        {"text": "队列积累。", "start": 2.1, "end": 3.2},
    ]
    compile_motion(s, words, 30)
    assert s.compiled_events[0].start_frame == 63
    assert s.compiled_events[0].end_frame == 78
    assert s.compiled_events[0].timing_source == "measured_words"
    words[1]["start"] = 2.6
    compile_motion(s, words, 30)
    assert s.compiled_events[0].start_frame == 78


def test_motion_rejects_missing_anchors_unmeasured_and_out_of_bounds():
    s = scene()
    with pytest.raises(TimelineConflict, match="measured"):
        compile_motion(s, [], 30)
    compile_motion(s, [], 30, allow_estimated=True)
    assert s.compiled_events[0].timing_source == "estimated_draft"
    s.motion.events[0].anchor.phrase = "不存在的短语"
    with pytest.raises(TimelineConflict, match="Missing"):
        compile_motion(s, [], 30, allow_estimated=True)
    s.motion.events[0].anchor.phrase = "请求"
    s.motion.events[0].anchor.offset_ms = -1000
    with pytest.raises(TimelineConflict, match="budget"):
        compile_motion(s, [], 30, allow_estimated=True)


def test_motion_references_and_output_profile_are_validated():
    value = scene().motion.model_dump()
    value["events"][0]["target"] = "invented"
    with pytest.raises(ValueError):
        SceneSpec.model_validate(value)
    b = Brief(title="Test", prompt="Test", render_profile={"resolution": "4k"})
    assert (b.render_profile.width, b.render_profile.height) == (3840, 2160)
    with pytest.raises(ValueError):
        StoryboardIR(title="Test", language="zh-CN", audience="general", scenes=[scene()], width=3840)


def test_voice_cache_tracks_actual_voice_model_speed_and_service(settings):
    first = voice_cache_key("相同文字", "zh-CN", "edge", settings)
    settings.edge_voice = "zh-CN-YunjianNeural"
    assert first != voice_cache_key("相同文字", "zh-CN", "edge", settings)
    assert first != voice_cache_key("相同文字", "zh-CN", "edge", settings, VoiceSpec(speed=1.1))
    first = voice_cache_key("x", "en-US", "ming", settings)
    settings.ming_model = "another-model"
    assert first != voice_cache_key("x", "en-US", "ming", settings)
    settings.tts_revision = "new-reference-hash"
    assert first != voice_cache_key("x", "en-US", "ming", settings)
    with pytest.raises(ValueError, match="configured reference"):
        voice_configuration("qwen", settings, VoiceSpec(voice_id="unsupported"))


def test_waveform_is_measured_and_silence_is_detected(tmp_path):
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        output.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(i * 0.07))) for i in range(4800)))
    measured = waveform(path)
    assert measured["duration"] == 0.1 and not measured["silent"]
    assert len(measured["peaks"]) <= 600 and 0.35 < max(measured["peaks"]) < 0.38
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        output.writeframes(b"\0" * 9600)
    assert waveform(path)["silent"]


def test_4k_frame_gate_preserves_dimension_validation(tmp_path):
    path = tmp_path / "frame.png"
    image = Image.new("RGB", (3840, 2160), "white")
    ImageDraw.Draw(image).rectangle((200, 200, 1000, 1000), fill="blue")
    image.save(path)
    assert inspect_frame(path, 3840, 2160)
    with pytest.raises(EngineeringError):
        inspect_frame(path)
    with pytest.raises(EngineeringError):
        source_path("src/motion-kit.tsx")


def test_compare_is_tenant_scoped_and_reports_fields(client, headers, db, settings):
    from explainer.api import insert_revision

    p = client.post("/api/v1/projects", headers=headers, json={"name": "Compare"}).json()["id"]
    board = StoryboardIR(title="x", language="zh-CN", audience="general", scenes=[scene()])
    first = insert_revision(db, settings, "local", p, Brief(title="x", prompt="x"), storyboard=board)
    board.scenes[0].title = "Changed title"
    second = insert_revision(db, settings, "local", p, Brief(title="x", prompt="x"), storyboard=board)
    url = f"/api/v1/revisions/{second['revision_id']}/compare/{first['revision_id']}"
    result = client.get(url, headers=headers)
    assert result.status_code == 200
    assert result.json()["changed_scenes"] == [{"id": "queue", "fields": ["title"]}]
    assert client.get(url, headers={"Authorization": "Bearer " + "b" * 32}).status_code == 404


def test_mcp_bridge_preserves_auth_and_does_not_follow_redirects():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"state": "QUEUED"})

    api = VideoAPI("http://localhost:8000", "private-key", httpx.MockTransport(respond))
    assert api.request("POST", "/api/v3/videos", {"brief": {"title": "x"}})["state"] == "QUEUED"
    assert seen[0].headers["authorization"] == "Bearer private-key"
    assert json.loads(seen[0].content)["brief"]["title"] == "x"
    api.client.close()
    for value in ["../jobs", "x?token=secret", "a/b", ""]:
        with pytest.raises(ValueError):
            safe_id(value)


def test_current_motion_evidence_is_required_before_acceptance(tmp_path):
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.controller import EngineeringController
    from explainer.services.engineering.contracts import EngineeringAction, SourceEdit

    media = tmp_path / "media"
    media.mkdir()
    w = Workspace(tmp_path / "w")
    w.prepare({"motion_review_required": True, "scenes": [], "total_frames": 30}, media)
    w.edit([SourceEdit(path="src/Video.tsx", content="export default function V(){return null}")])
    fingerprint = w.fingerprint()
    w.state.update(
        build_hash=fingerprint,
        preview_hash=fingerprint,
        frames=[{"name": "keyframe.png"}],
        motion_frames=[{"name": "strip.png"}],
        clips=[{"name": "clip.mp4"}],
    )
    c = EngineeringController(w, None, None, lambda _: None, lambda *a: None, lambda: None)
    review = dict(
        accepted=True,
        legibility=5,
        visual_explanation=5,
        timing=5,
        issues=[],
        inspected_frames=["keyframe.png"],
    )
    with pytest.raises(EngineeringError, match="Motion review"):
        c.apply(EngineeringAction(action="review", summary="Test", files=[], review=review))
    review.update(motion_continuity=4, inspected_motion_frames=["strip.png"])
    c.apply(EngineeringAction(action="review", summary="Test", files=[], review=review))
    assert w.state["review_hash"] == fingerprint
    w.edit([SourceEdit(path="src/Video.tsx", content="export default function V(){return <div/>}")])
    assert w.state["review_hash"] is None and w.state["clips"] == []


def test_voice_spec_fork_invalidates_audio_and_compiled_events(client, db, headers, settings):
    from explainer.api import insert_revision
    from explainer.storage import Storage

    project = client.post("/api/v1/projects", headers=headers, json={"name": "Voice fork"}).json()["id"]
    board = StoryboardIR(title="x", language="zh-CN", audience="general", scenes=[scene()])
    audio = Storage(settings, db).put("local", b"fixture-audio", "audio", "test.wav", "audio/wav")
    board.scenes[0].audio_id = audio["id"]
    board.scenes[0].cues = [Cue(start=0, end=1, text="Old timing")]
    compile_motion(board.scenes[0], [], 30, allow_estimated=True)
    original = insert_revision(db, settings, "local", project, Brief(title="x", prompt="x"), storyboard=board)
    result = client.post(
        f"/api/v1/revisions/{original['revision_id']}/fork",
        headers=headers,
        json={
            "expected_version": db.one(
                "SELECT version FROM revisions WHERE id=?", (original["revision_id"],)
            )["version"],
            "auto_render": False,
            "brief": {"title": "x", "prompt": "x", "voice_spec": {"speed": 1.1}},
        },
    )
    assert result.status_code == 202
    value = json.loads(
        db.one("SELECT storyboard FROM revisions WHERE id=?", (result.json()["revision_id"],))["storyboard"]
    )["scenes"][0]
    assert value["audio_id"] is None and value["cues"] == [] and value["compiled_events"] == []


def test_pattern_limits_reject_silently_dropped_or_overflowing_content():
    base = {"purpose": "Show every supplied element", "pattern": "compare"}
    elements = [{"id": f"card{i}", "label": "Card"} for i in range(4)]
    with pytest.raises(ValueError, match="1–3"):
        SceneSpec(**base, elements=elements)
    with pytest.raises(ValueError, match="overview"):
        SceneSpec(**base, layout="fan", elements=elements[:2])
    fan = SceneSpec(purpose=base["purpose"], pattern="overview", layout="fan", elements=elements)
    assert fan.layout == "fan" and len(fan.elements) == 4
    with pytest.raises(ValueError, match="20 characters"):
        SceneSpec(purpose=base["purpose"], pattern="graph", elements=[{"id": "x", "label": "长" * 21}])


def test_edge_stream_preserves_measured_timing_and_applies_speed(settings, tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from explainer.adapters.voice import synthesize
    from explainer.adapters.alignment import validate_words

    received = {}

    class Communicate:
        def __init__(self, text, voice, **kwargs):
            received.update(text=text, voice=voice, **kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"actual-provider-audio-chunk"}
            yield {"type": "WordBoundary", "text": "请求", "offset": 2_000_000, "duration": 8_000_000}
            yield {"type": "WordBoundary", "text": "增加", "offset": 12_000_000, "duration": 8_000_000}

    class Runner:
        checks = 0

        def guard(self):
            self.checks += 1

        def run(self, args, **kwargs):
            if args[0] == "ffprobe":
                return '{"format":{"duration":"3.0"}}'
            assert args[0] == "ffmpeg" and "atempo=1.1" in args[args.index("-af") + 1]
            return ""

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=Communicate))
    settings.tts_proxy = "http://configured-proxy:8080"
    runner = Runner()
    result = synthesize(
        Scene(id="test", type="flow", title="Test", narration="请求增加"),
        "zh-CN",
        "edge",
        settings,
        tmp_path,
        runner,
        VoiceSpec(speed=1.1),
    )
    assert received["boundary"] == "WordBoundary" and received["proxy"] == settings.tts_proxy
    assert result["alignment_method"] == "native_words" and runner.checks == 3
    assert result["words"][0]["start"] == pytest.approx(0.2 / 1.1)
    assert result["words"][1]["end"] == pytest.approx(2 / 1.1)
    validate_words(result["words"], "请求增加", result["duration"])
    assert (tmp_path / "test-raw.wav").read_bytes() == b"actual-provider-audio-chunk"


def test_edge_preflight_uses_native_timing_but_keeps_explicit_forced_alignment(settings, monkeypatch):
    from explainer.services.engineering.integration import professional_preflight
    from explainer.services.engineering.workspace import EngineeringError

    monkeypatch.setattr(
        "explainer.services.engineering.integration.importlib.util.find_spec", lambda _: object()
    )
    brief = Brief(title="Test", prompt="Test", voice="edge", video_mode="engineering", agent_engine="codex")
    professional_preflight(brief, settings)
    settings.alignment_engine = "stable-ts"
    with pytest.raises(EngineeringError, match="对齐"):
        professional_preflight(brief, settings)
    settings.alignment_engine = "auto"
    monkeypatch.setattr("explainer.services.engineering.integration.importlib.util.find_spec", lambda _: None)
    with pytest.raises(EngineeringError, match="apps/api"):
        professional_preflight(brief, settings)
