"""Real compiler -> repair -> render test of FIXED trusted authored code only.
Never a host fallback for uploaded/native-generated source. No real Agent inference.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.services.engineering.workspace import Workspace
from explainer.services.engineering.controller import EngineeringController
from explainer.services.engineering.contracts import EngineeringAction
from explainer.services.process import Runner, ProcessError
from explainer.services.quality import inspect_video

out = ROOT / ".verify-engineering"
if out.exists():
    shutil.rmtree(out)  # Fixed disposable fixture directory only; never a user input.
out.mkdir(exist_ok=True)
media = out / "media"
media.mkdir(exist_ok=True)
with zipfile.ZipFile(ROOT / "examples/generated/qwen-v2/editable-project.zip") as z:
    props = json.loads(z.read("project.json"))
    manifest = json.loads(z.read("manifest.json"))
    for scene in props["scenes"]:
        if scene.get("audio_id"):
            item = manifest[scene["audio_id"]]
            name = Path(item["path"]).name
            (media / name).write_bytes(z.read(item["path"]))
            scene["audio_src"] = name
shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
w = Workspace(out / "session")
w.prepare(props, media)
link = w.project / "node_modules"
if not link.exists():
    link.symlink_to(ROOT / "node_modules", target_is_directory=True)
source = (ROOT / "examples/engineering-fixture/Video.tsx").read_text()
broken = 'import React from "react"; export default function Fixture(){return <div>{UNDEFINED_FIXTURE_NAME}</div>}'


class AuthoredTools:
    def execute(self, workspace, kind):
        # Only these two fixed, reviewed fixture bodies may run on host.
        assert workspace.state["files"] == {"src/Video.tsx": source} or workspace.state[
            "files"
        ] == {"src/Video.tsx": broken}
        target = workspace.root / f"tool-{workspace.state['iteration']}-{kind}"
        target.mkdir(exist_ok=True)
        try:
            Runner().run(
                [
                    "node",
                    ROOT / "packages/engineering-template/render.mjs",
                    workspace.project,
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
                {**f, "name": str((target / f["name"]).relative_to(workspace.root))}
                for f in result["frames"]
            ]
        if kind == "final" and result["ok"]:
            result["video"] = str(target / "video.mp4")
        return result


class AuthoredDecisionFixture:
    def decide(self, workspace, plan):
        i = workspace.state["iteration"]
        actions = [
            ("write_files", broken),
            ("build", None),
            ("write_files", source),
            ("build", None),
            ("render_preview", None),
            ("review", None),
            ("finish", None),
        ]
        kind, text = actions[i]
        if i == 2:
            assert workspace.state["journal"][-1]["data"]["ok"] is False
        review = (
            {
                "accepted": True,
                "legibility": 5,
                "visual_explanation": 5,
                "timing": 5,
                "issues": [],
                "inspected_frames": [f["name"] for f in workspace.state["frames"]],
            }
            if kind == "review"
            else None
        )
        return EngineeringAction(
            action=kind,
            summary="Authored integration fixture",
            files=[{"path": "src/Video.tsx", "content": text}] if text else [],
            review=review,
        )


result = EngineeringController(
    w,
    AuthoredDecisionFixture(),
    AuthoredTools(),
    lambda _: None,
    lambda *args: None,
    lambda: None,
    12,
).run({"fixture": True})
metadata = inspect_video(result["video"], Runner(), props["total_frames"])
dest = out / "deliverables"
dest.mkdir(exist_ok=True)
shutil.copyfile(result["video"], dest / "engineering-fixture.mp4")
w.export(
    dest / "remotion-project.zip", {"fixture": True, "actual_native_inference": False}
)
report = {
    "result": "passed",
    "actual_tsc_and_remotion": True,
    "compiler_error_observed_and_repaired": True,
    "frames": metadata["frames"],
    "sampled_keyframes": len(w.state["frames"]),
    "full_decode": metadata["decode"],
    "actual_native_inference": False,
    "review": "programmed fixture; manual visual inspection separate",
    "voice": "reused actual approved Qwen sample; no new TTS inference",
    "generated_code_isolation_tested": False,
}
(out / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
