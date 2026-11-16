import json
import pytest

from explainer.config import ROOT
from explainer.domain import Brief
from explainer.services.engineering.contracts import EngineeringAction, SourceEdit, ProductionPlan
from explainer.services.engineering.workspace import Workspace, EngineeringError, source_path
from explainer.services.engineering.controller import EngineeringController
from explainer.services.engineering.integration import check_font, professional_preflight
from explainer.adapters.native_contract import validate_design
from explainer.services.ingestion import analyze


def plan():
    design = json.loads((ROOT / "examples/native-agent-design.json").read_text())
    return ProductionPlan(
        objective="Explain the request lifecycle visually",
        story_arc=["Input", "Processing", "Result"],
        art_direction="Use legible Chinese typography and real process movement",
        voice_direction="Professional clear male narration with natural pauses",
        shots=[
            {
                "scene_id": "explain",
                "visual": "Two systems exchanging a visible request",
                "movement": "Animate the request between the two systems",
                "assets": [],
            }
        ],
        storyboard=design,
    )


def action(kind, **fields):
    return EngineeringAction(
        action=kind, summary="Test action", files=fields.get("files", []), review=fields.get("review")
    )


@pytest.fixture
def workspace(tmp_path):
    w = Workspace(tmp_path / "engineering")
    media = tmp_path / "media"
    media.mkdir()
    (media / "noto.otf").write_bytes(b"test font fixture")
    w.prepare({"total_frames": 600, "scenes": []}, media)
    return w


class Tools:
    def __init__(self):
        self.calls = []

    def execute(self, w, kind):
        self.calls.append(kind)
        if kind == "preview":
            (w.root / "frame.png").write_bytes(b"explicit non-image protocol fixture")
            return {"ok": True, "frames": [{"name": "frame.png", "frame": 30}]}
        return {"ok": True, "video": "authored-fixture.mp4"}


def controller(w, tools=None):
    return EngineeringController(w, None, tools or Tools(), lambda _: None, lambda *args: None, lambda: None)


def accepted_review():
    return {
        "accepted": True,
        "legibility": 5,
        "visual_explanation": 5,
        "timing": 5,
        "issues": [],
        "inspected_frames": ["frame.png"],
    }


def test_engineering_professional_never_uses_espeak_or_silence():
    b = Brief(title="Test", prompt="Test", video_mode="engineering", agent_engine="codex")
    assert b.voice == "qwen" and b.require_alignment
    for engine in ["none", "espeak"]:
        with pytest.raises(ValueError):
            Brief(title="Test", prompt="Test", video_mode="engineering", agent_engine="codex", voice=engine)
    with pytest.raises(ValueError):
        Brief(title="Test", prompt="Test", video_mode="engineering")
    assert Brief(title="Legacy", prompt="Legacy").video_mode == "template"


@pytest.mark.parametrize(
    "path",
    [
        "../src/a.tsx",
        "src/../x.tsx",
        "/src/a.tsx",
        "src\\a.tsx",
        "src/Root.tsx",
        "src/index.tsx",
        "src/contracts.ts",
        "package.json",
        "src/.hidden.ts",
        "src/a.js",
        "src//a.tsx",
    ],
)
def test_generated_source_paths_reject_escape_and_trusted_tool_changes(path):
    with pytest.raises(EngineeringError):
        source_path(path)


def test_file_patch_is_atomic_and_invalidates_all_gates(workspace):
    workspace.state["build_hash"] = "old"
    workspace.state["review_hash"] = "old"
    before = (workspace.project / "src/Video.tsx").read_text()
    with pytest.raises(EngineeringError):
        workspace.edit(
            [
                SourceEdit(path="src/Video.tsx", content="changed"),
                SourceEdit(path="src/Root.tsx", content="tampered"),
            ]
        )
    assert (workspace.project / "src/Video.tsx").read_text() == before
    workspace.edit([SourceEdit(path="src/Video.tsx", content="export default function Video(){return null}")])
    assert workspace.state["build_hash"] is None and workspace.state["review_hash"] is None


def test_finish_requires_real_current_build_preview_and_review(workspace):
    c = controller(workspace)
    with pytest.raises(EngineeringError):
        c.apply(action("finish"))
    c.apply(
        action(
            "write_files",
            files=[SourceEdit(path="src/Video.tsx", content="export default function Video(){return null}")],
        )
    )
    c.apply(action("build"))
    c.apply(action("render_preview"))
    with pytest.raises(EngineeringError):
        c.apply(action("finish"))
    c.apply(action("review", review=accepted_review()))
    c.apply(action("finish"))
    assert workspace.state["finished"]
    workspace.edit(
        [SourceEdit(path="src/Video.tsx", content="export default function Video(){return <div/>}")]
    )
    with pytest.raises(EngineeringError):
        c.apply(action("finish"))


def test_review_must_inspect_actual_frames_and_meet_quality_threshold(workspace):
    c = controller(workspace)
    c.apply(action("build"))
    c.apply(action("render_preview"))
    review = accepted_review()
    review["inspected_frames"] = ["invented.png"]
    with pytest.raises(EngineeringError):
        c.apply(action("review", review=review))
    review = accepted_review()
    review["visual_explanation"] = 2
    c.apply(action("review", review=review))
    assert workspace.state["review_hash"] is None
    review = accepted_review()
    review["issues"] = ["Text is clipped"]
    c.apply(action("review", review=review))
    assert workspace.state["review_hash"] is None


def test_generated_props_change_invalidates_previously_reviewed_source(workspace):
    c = controller(workspace)
    c.apply(
        action(
            "write_files",
            files=[SourceEdit(path="src/Video.tsx", content="export default function Video(){return null}")],
        )
    )
    c.apply(action("build"))
    c.apply(action("render_preview"))
    c.apply(action("review", review=accepted_review()))
    (workspace.project / "props.json").write_text('{"total_frames":900}')
    with pytest.raises(EngineeringError):
        c.apply(action("finish"))


def test_build_failure_observation_enters_repair_loop(workspace):
    class FailingTools(Tools):
        def execute(self, w, kind):
            if kind == "build" and not self.calls:
                self.calls.append(kind)
                return {"ok": False, "diagnostic": "real compiler fixture: unknown name"}
            return super().execute(w, kind)

    sequence = [
        action("write_files", files=[SourceEdit(path="src/Video.tsx", content="bad")]),
        action("build"),
        action("write_files", files=[SourceEdit(path="src/Video.tsx", content="fixed")]),
        action("build"),
        action("render_preview"),
        action("review", review=accepted_review()),
        action("finish"),
    ]

    class Agent:
        def decide(self, w, p):
            if w.state["iteration"] == 2:
                assert w.state["journal"][-1]["data"]["ok"] is False
            return sequence[w.state["iteration"]]

    c = EngineeringController(
        workspace, Agent(), FailingTools(), lambda _: None, lambda *args: None, lambda: None, 10
    )
    assert c.run({})["ok"]
    assert len([x for x in workspace.state["journal"] if x["kind"] == "build"]) == 2


def test_state_restores_authored_files_and_source_fingerprint(workspace, tmp_path):
    workspace.edit([SourceEdit(path="src/Video.tsx", content="export default function X(){return null}")])
    workspace.record("authored", {"ok": True})
    restored = Workspace(workspace.root)
    restored.prepare({"total_frames": 600, "scenes": []}, tmp_path / "media")
    assert restored.fingerprint() == workspace.fingerprint()
    assert restored.state["iteration"] == 1


def test_native_production_plan_requires_visual_and_motion_per_scene():
    p = plan()
    assert p.shots
    broken = p.model_dump()
    broken["shots"][0]["scene_id"] = "unrelated"
    with pytest.raises(ValueError):
        ProductionPlan.model_validate(broken)


def test_font_failure_or_replacement_char_aborts(settings):
    brief = Brief(title="中文标题", prompt="中文讲解")
    board = validate_design(plan().storyboard.model_dump(), analyze(brief), brief)
    with pytest.raises(EngineeringError):
        check_font(board, ROOT / "assets/missing.otf")
    board.scenes[0].title = "乱码\ufffd"
    with pytest.raises(EngineeringError, match="replacement"):
        check_font(board, ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf")
    with pytest.raises(EngineeringError):
        professional_preflight(
            Brief(title="Test", prompt="Test", agent_engine="codex", video_mode="engineering"), settings
        )


def test_engineering_planning_is_connected_to_existing_pipeline(settings, db, monkeypatch):
    import time
    from explainer.api import insert_revision
    from explainer.worker import run_once

    brief = Brief(
        title="Test",
        prompt="Test",
        video_mode="engineering",
        agent_engine="codex",
        quality_profile="draft",
        voice="none",
        mode="storyboard",
    )

    def fixture(self):
        return (
            plan(),
            validate_design(plan().storyboard.model_dump(), analyze(brief), brief),
            {"fixture": True},
        )

    monkeypatch.setattr("explainer.services.engineering.agent.NativeEngineeringAgent.plan", fixture)
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("engineering", "local", "Engineering", time.time()))
    result = insert_revision(db, settings, "local", "engineering", brief)
    run_once(settings, db, job_id=result["job_id"])
    assert db.one("SELECT state FROM jobs WHERE id=?", (result["job_id"],))["state"] == "SUCCEEDED"
    assert db.one(
        "SELECT * FROM outputs WHERE revision_id=? AND role='production_plan'", (result["revision_id"],)
    )


def test_no_generated_execution_when_docker_unavailable(workspace, settings, monkeypatch):
    from explainer.services.engineering.tools import RenderTools
    from explainer.services.process import Runner

    monkeypatch.setattr("explainer.services.engineering.tools.shutil.which", lambda _: None)
    with pytest.raises(EngineeringError, match="未在宿主机执行"):
        RenderTools(settings, Runner()).execute(workspace, "build")


def test_frame_gate_rejects_blank_and_wrong_size(tmp_path):
    from PIL import Image, ImageDraw
    from explainer.services.engineering.tools import inspect_frame

    target = tmp_path / "frame.png"
    Image.new("RGB", (1920, 1080), "white").save(target)
    with pytest.raises(EngineeringError, match="empty"):
        inspect_frame(target)
    image = Image.new("RGB", (1920, 1080), "white")
    ImageDraw.Draw(image).rectangle((100, 100, 500, 500), fill="blue")
    image.save(target)
    assert len(inspect_frame(target)) == 64
    Image.new("RGB", (10, 10), "blue").save(target)
    with pytest.raises(EngineeringError, match="1920"):
        inspect_frame(target)


def test_resume_of_accepted_source_does_not_reinvoke_agent(workspace):
    c = controller(workspace)
    c.apply(
        action(
            "write_files",
            files=[SourceEdit(path="src/Video.tsx", content="export default function X(){return null}")],
        )
    )
    c.apply(action("build"))
    c.apply(action("render_preview"))
    c.apply(action("review", review=accepted_review()))
    c.apply(action("finish"))

    class NoMoreCalls:
        def decide(self, *args):
            raise AssertionError("Accepted source must not request another paid decision")

    c.agent = NoMoreCalls()
    assert c.run({})["ok"]


def test_invalid_native_action_is_observed_and_bounded(workspace):
    class InvalidAgent:
        def decide(self, *args):
            raise ValueError("Invalid model output")

    c = EngineeringController(
        workspace, InvalidAgent(), Tools(), lambda _: None, lambda *args: None, lambda: None, 5
    )
    with pytest.raises(EngineeringError, match="上限"):
        c.run({})
    assert len(workspace.state["journal"]) == 5


def test_generated_project_exports_authored_source_and_reviews(workspace, tmp_path):
    import zipfile

    workspace.edit([SourceEdit(path="src/Video.tsx", content="export default function Video(){return null}")])
    workspace.state["review"] = {"accepted": True, "reviewer": "explicit test fixture"}
    workspace.record("export.test", {"ok": True})
    target = tmp_path / "project.zip"
    workspace.export(target, {"objective": "Test"})
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert z.read("src/Video.tsx").decode().startswith("export default")
        for name in [
            "package-lock.json",
            "render.mjs",
            "src/Root.tsx",
            "production-plan.json",
            "visual-review.json",
            "authoring-journal.json",
        ]:
            assert name in z.namelist()
        assert not any("node_modules" in name for name in z.namelist())


def test_v3_api_defaults_to_engineering_and_qwen(client, db, headers):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Engineering API"}).json()
    response = client.post(
        "/api/v3/videos",
        headers=headers,
        json={
            "project_id": project["id"],
            "brief": {"title": "Explain", "prompt": "Explain a software project", "mode": "storyboard"},
        },
    )
    assert response.status_code == 202
    brief = json.loads(
        db.one("SELECT brief FROM revisions WHERE id=?", (response.json()["revision_id"],))["brief"]
    )
    assert (
        brief["video_mode"] == "engineering" and brief["agent_engine"] == "codex" and brief["voice"] == "qwen"
    )
    rejected = client.post(
        "/api/v3/videos",
        headers=headers,
        json={
            "project_id": project["id"],
            "brief": {"title": "Explain", "prompt": "Explain", "video_mode": "template"},
        },
    )
    assert rejected.status_code == 422


def test_a_new_failed_preview_cannot_reuse_old_acceptance(workspace):
    c = controller(workspace)
    c.apply(
        action(
            "write_files",
            files=[SourceEdit(path="src/Video.tsx", content="export default function X(){return null}")],
        )
    )
    c.apply(action("build"))
    c.apply(action("render_preview"))
    c.apply(action("review", review=accepted_review()))

    class BrokenTools:
        def execute(self, *args):
            raise EngineeringError("New render failed")

    c.tools = BrokenTools()
    with pytest.raises(EngineeringError):
        c.apply(action("render_preview"))
    with pytest.raises(EngineeringError):
        c.apply(action("finish"))
    assert workspace.state["review_hash"] is None and workspace.state["frames"] == []
