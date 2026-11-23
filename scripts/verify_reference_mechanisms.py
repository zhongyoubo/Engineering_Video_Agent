"""Real rendering of fixed reviewed source/data ONLY. Silent draft, not model/voice acceptance."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from explainer.domain import Scene, StoryboardIR
    from explainer.services.motion import compile_motion
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.contracts import SourceEdit
    from explainer.services.engineering.tools import read_receipt, validate_motion_clip
    from explainer.services.process import Runner
    from explainer.services.quality import inspect_video
    from PIL import Image, ImageChops, ImageStat

    out = ROOT / ".verify-reference-mechanisms"
    out.mkdir(exist_ok=True)
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    scenes = []
    cursor = 0
    for data in json.loads(
        (ROOT / "examples/reference-mechanisms/scenes.json").read_text()
    )["scenes"]:
        scene = Scene.model_validate(data)
        scene.start_frame = cursor
        cursor += scene.frames
        compile_motion(scene, [], 30, allow_estimated=True)
        scenes.append(scene)
    board = StoryboardIR(
        title="参考表达工程验证",
        language="zh-CN",
        audience="general",
        scenes=scenes,
        total_frames=cursor,
    )
    props = board.model_dump()
    props.update(width=1920, height=1080, motion_review_required=True)
    w = Workspace(out / "engineering")
    w.prepare({**props, "design_pack": "editorial_warm"}, media)
    w.edit(
        [
            SourceEdit(
                path="src/Video.tsx",
                content=(ROOT / "examples/reference-mechanisms/Video.tsx").read_text(),
            )
        ]
    )
    modules = w.project / "node_modules"
    if not modules.exists():
        modules.symlink_to(ROOT / "node_modules", target_is_directory=True)
    runner = Runner()
    stamp = w.fingerprint()
    for action in ["build", "preview", "final"]:
        target = out / action
        runner.run(
            [
                "node",
                ROOT / "packages/engineering-template/render.mjs",
                w.project,
                action,
                target,
            ],
            timeout=1200,
            env=os.environ.copy(),
        )
        result = read_receipt(target / "result.json", action)
        assert result["ok"] and w.fingerprint() == stamp
        if action == "preview":
            for clip in result["clips"]:
                scene = next(s.model_dump() for s in scenes if s.id == clip["scene_id"])
                metadata = json.loads(
                    runner.run(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_streams",
                            "-show_format",
                            "-of",
                            "json",
                            target / clip["name"],
                        ]
                    )
                )
                validate_motion_clip(clip, scene, metadata, 30)
    # A second real preview with the same source/content and another protected theme.
    v = Workspace(out / "tech-engineering")
    v.prepare({**props, "design_pack": "workspace_tech"}, media)
    v.edit(
        [
            SourceEdit(
                path="src/Video.tsx",
                content=(ROOT / "examples/reference-mechanisms/Video.tsx").read_text(),
            )
        ]
    )
    if not (v.project / "node_modules").exists():
        (v.project / "node_modules").symlink_to(
            ROOT / "node_modules", target_is_directory=True
        )
    runner.run(
        [
            "node",
            ROOT / "packages/engineering-template/render.mjs",
            v.project,
            "preview",
            out / "tech-preview",
        ],
        timeout=1200,
        env=os.environ.copy(),
    )
    assert read_receipt(out / "tech-preview/result.json", "preview")["ok"]
    a = Image.open(out / "preview/frame-000067.png").convert("RGB")
    b = Image.open(out / "tech-preview/frame-000067.png").convert("RGB")
    theme_delta = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean)
    assert theme_delta > 1
    w.export(
        out / "Reference_Mechanisms_Project.zip",
        {
            "fixed_fixture": True,
            "native_inference": False,
            "audio": "none",
            "timing": "estimated_draft",
        },
    )
    video = out / "final/video.mp4"
    result = dict(
        source_hash=stamp,
        media=inspect_video(video, runner, board.total_frames),
        video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
        theme_pixel_difference=theme_delta,
        features=[
            "shared parameter dial/tree/metric",
            "integrated reservoir and queue rates",
            "24-line paged code focus",
            "shared theme",
        ],
        native_inference=False,
        image_generation=False,
        audio="none",
        timing="estimated_draft",
        human_playback_and_listening=False,
        isolation="fixed reviewed host verifier only",
    )
    (out / "verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
