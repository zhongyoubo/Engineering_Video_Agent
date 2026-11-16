"""Full real pipeline/storage/export check with fixed authored native decisions.
Only the known fixture source runs on host; production RenderTools is never relaxed.
"""

import json, os, shutil, sys, time, zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief, StoryboardIR
from explainer.api import insert_revision
from explainer.worker import run_once
from explainer.storage import Storage
from explainer.services.engineering.contracts import ProductionPlan, EngineeringAction
from explainer.services.process import Runner, ProcessError

out = ROOT / ".verify-engineering-pipeline"
if out.exists():
    shutil.rmtree(out)
settings = Settings(
    data_dir=out / "data",
    api_token="pipeline-fixture-only-key-1234567890",
    chrome_executable=os.getenv("CHROME_EXECUTABLE", ""),
).prepare()
db = Database(settings.data_dir)
db.execute(
    "INSERT INTO projects VALUES(?,?,?,?)",
    ("p", "local", "Pipeline fixture", time.time()),
)
brief = Brief(
    title="工程制作闭环验收",
    prompt="解释从内容到视频的工程流程",
    agent_engine="codex",
    video_mode="engineering",
    quality_profile="draft",
    voice="none",
    target_seconds=20,
    duration_mode="exact",
)
with zipfile.ZipFile(ROOT / "examples/generated/qwen-v2/editable-project.zip") as z:
    board = StoryboardIR.model_validate(json.loads(z.read("project.json")))
for scene in board.scenes:
    scene.audio_id = None
    scene.cues = []
    scene.media_id = None
fields = [
    "id",
    "type",
    "title",
    "subtitle",
    "narration",
    "bullets",
    "code",
    "claim_ids",
    "evidence_ids",
    "duration",
    "diagram",
]
plan = ProductionPlan(
    objective="Verify the entire engineering pipeline with a fixed authored fixture",
    story_arc=["Understand", "Create", "Deliver"],
    art_direction="Clear Chinese typography with real React and SVG motion",
    voice_direction="This is a deliberate silent draft verification, not a professional voice sample",
    shots=[
        {
            "scene_id": s.id,
            "visual": "Explain this scene through a custom React component",
            "movement": "Progressive reveal and timed changes following actual frames",
            "assets": [],
        }
        for s in board.scenes
    ],
    storyboard={
        "protocol": "1.0",
        "scenes": [
            {k: s.model_dump(mode="json")[k] for k in fields} for s in board.scenes
        ],
    },
)
source = (ROOT / "examples/engineering-fixture/Video.tsx").read_text()
broken = 'import React from "react"; export default function X(){return <div>{FIXTURE_MISSING_NAME}</div>}'


def authored_plan(self):
    return plan, board, {"fixture": True, "actual_native_inference": False}


def authored_decide(self, w, p):
    kind, text = [
        ("write_files", broken),
        ("build", None),
        ("write_files", source),
        ("build", None),
        ("render_preview", None),
        ("review", None),
        ("finish", None),
    ][w.state["iteration"]]
    review = (
        {
            "accepted": True,
            "legibility": 5,
            "visual_explanation": 5,
            "timing": 5,
            "issues": [],
            "inspected_frames": [f["name"] for f in w.state["frames"]],
        }
        if kind == "review"
        else None
    )
    return EngineeringAction(
        action=kind,
        summary="Fixed authored pipeline test",
        files=[{"path": "src/Video.tsx", "content": text}] if text else [],
        review=review,
    )


def trusted_tool(self, w, kind):
    assert w.state["files"] in [{"src/Video.tsx": source}, {"src/Video.tsx": broken}]
    node_modules = w.project / "node_modules"
    if not node_modules.exists():
        node_modules.symlink_to(ROOT / "node_modules", target_is_directory=True)
    target = w.root / f"fixture-{w.state['iteration']}-{kind}"
    target.mkdir(exist_ok=True)
    try:
        Runner().run(
            [
                "node",
                ROOT / "packages/engineering-template/render.mjs",
                w.project,
                kind,
                target,
            ],
            timeout=300,
        )
    except ProcessError:
        pass
    result = json.loads((target / "result.json").read_text())
    if kind == "preview" and result["ok"]:
        result["frames"] = [
            {**f, "name": str((target / f["name"]).relative_to(w.root))}
            for f in result["frames"]
        ]
    if kind == "final" and result["ok"]:
        result["video"] = str(target / "video.mp4")
    return result


with (
    patch(
        "explainer.services.engineering.agent.NativeEngineeringAgent.plan",
        authored_plan,
    ),
    patch(
        "explainer.services.engineering.agent.NativeEngineeringAgent.decide",
        authored_decide,
    ),
    patch("explainer.services.engineering.tools.RenderTools.execute", trusted_tool),
):
    r = insert_revision(db, settings, "local", "p", brief)
    run_once(settings, db, job_id=r["job_id"])
job = db.one("SELECT * FROM jobs WHERE id=?", (r["job_id"],))
assert job["state"] == "SUCCEEDED", job
roles = {
    x["role"]: x["asset_id"]
    for x in db.all("SELECT * FROM outputs WHERE revision_id=?", (r["revision_id"],))
}
assert {
    "video",
    "engineering_project",
    "production_plan",
    "visual_review",
    "authoring_journal",
    "engineering_state",
    "engineering_preview",
    "keyframes",
    "package",
} <= set(roles)
store = Storage(settings, db)
_, path = store.get("local", roles["engineering_project"])
with zipfile.ZipFile(path) as z:
    assert z.read("src/Video.tsx").decode() == source
    assert "AGENTS.md" in z.namelist()
_, state_path = store.get("local", roles["engineering_state"])
state = json.loads(state_path.read_text())
assert state["finished"] and all(f.get("asset_id") for f in state["frames"])
_, package = store.get("local", roles["package"])
with zipfile.ZipFile(package) as z:
    assert "remotion-project.zip" in z.namelist()
report = {
    "result": "passed",
    "actual_native_inference": False,
    "actual_compiler_renderer_pipeline_storage_export": True,
    "persisted_steps": state["iteration"],
    "keyframe_assets": len(state["frames"]),
    "complete_source_delivered": True,
    "draft": True,
    "generated_code_isolation_tested": False,
}
(out / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
