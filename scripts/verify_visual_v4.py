"""Render fixed, reviewed reference-pattern fixtures. Never run uploaded/generated code on host.

No new TTS or native inference is performed. The three samples are explicitly silent drafts.
Usage: CHROME_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/verify_visual_v4.py
"""

import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.domain import Scene, StoryboardIR
from explainer.services.engineering.workspace import Workspace
from explainer.services.engineering.contracts import SourceEdit
from explainer.services.motion import compile_motion
from explainer.services.process import Runner
from explainer.services.quality import inspect_video
from explainer.services.engineering.tools import inspect_frame


def main():
    output = ROOT / ".verify-visual-v4"
    output.mkdir(exist_ok=True)
    media = output / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    definitions = [
        ("code_scan", "从代码到问题清单", ["扫描代码", "检查边界", "记录问题"]),
        ("depth", "少做而深做", ["分散投入", "持续深入"]),
        ("queue", "请求增加与并发限制", ["请求进入", "队列积累", "处理服务"]),
    ]
    scenes = []
    for index, (pattern, title, labels) in enumerate(definitions):
        scene = Scene(
            id=pattern,
            type="flow",
            title=title,
            narration="这是无配音的视觉工程测试样例。",
            duration=3,
            start_frame=index * 90,
            frames=90,
            code="function process(request) {\n  validate(request);\n  const result = run(request);\n  return result;\n}\n\n// Review input boundaries\n// Preserve execution evidence",
            motion={
                "purpose": "检验参考表达的布局与帧驱动运动",
                "pattern": pattern,
                "elements": [
                    {"id": f"element_{i}", "label": label}
                    for i, label in enumerate(labels)
                ],
                "events": [
                    {
                        "id": f"event_{i}",
                        "target": f"element_{i}",
                        "action": "progress",
                        "anchor": {"phrase": "这是", "offset_ms": i * 100},
                        "duration_ms": 2200,
                    }
                    for i in range(len(labels))
                ],
            },
        )
        compile_motion(scene, [], 30, allow_estimated=True)
        scenes.append(scene)
    board = StoryboardIR(
        title="参考表达工程样片（无配音草稿）",
        language="zh-CN",
        audience="developer",
        scenes=scenes,
        width=3840,
        height=2160,
        total_frames=270,
        design_pack="editorial_warm",
    )
    props = {**board.model_dump(), "motion_review_required": True}
    workspace = Workspace(output / "session")
    workspace.prepare(props, media)
    source = (ROOT / "examples/reference-patterns/Video.tsx").read_text()
    workspace.edit([SourceEdit(path="src/Video.tsx", content=source)])
    link = workspace.project / "node_modules"
    if not link.exists():
        link.symlink_to(ROOT / "node_modules", target_is_directory=True)
    runner = Runner()
    for action in ["build", "preview", "final"]:
        target = output / action
        target.mkdir(exist_ok=True)
        # Exactly this authored fixture, never an externally supplied source file.
        assert workspace.state["files"] == {"src/Video.tsx": source}
        try:
            runner.run(
                [
                    "node",
                    ROOT / "packages/engineering-template/render.mjs",
                    workspace.project,
                    action,
                    target,
                ],
                timeout=900,
                env=os.environ.copy(),
            )
        except Exception as error:
            result_path = target / "result.json"
            if result_path.exists():
                raise RuntimeError(result_path.read_text()) from error
            raise
        receipt = json.loads((target / "result.json").read_text())
        if not receipt.get("ok"):
            raise RuntimeError(receipt)
        if action == "preview":
            assert len(receipt["clips"]) == 3 and len(receipt["motion_frames"]) == 3
            for frame in receipt["frames"]:
                inspect_frame(target / frame["name"], 3840, 2160)
            for frame in receipt["motion_frames"]:
                inspect_frame(target / frame["name"], 1280, 360)
    metadata = inspect_video(output / "final/video.mp4", runner, 270, 3840, 2160)
    workspace.export(
        output / "remotion-project.zip", {"authored_fixture": True, "narration": "none"}
    )
    report = {
        "actual_compiler_renderer": True,
        "media": metadata,
        "scene_clips": 3,
        "keyframes": 9,
        "motion_sheets": 3,
        "actual_native_inference": False,
        "new_tts_inference": False,
        "generated_code_isolation_tested": False,
        "human_visual_and_listening_review": False,
        "source": "fixed reviewed repository fixture",
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
