"""ONLY fixed repository source/data. Real render checks, not native inference acceptance."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.domain import Scene, StoryboardIR
from explainer.semantic_scene import AssetRequirement
from explainer.services.motion import compile_motion
from explainer.services.engineering.tools import read_receipt, validate_motion_clip
from explainer.services.engineering.workspace import Workspace
from explainer.services.engineering.contracts import SourceEdit
from explainer.services.assets.registry import request_assets
from explainer.services.process import Runner
from explainer.services.quality import inspect_video
from PIL import Image, ImageChops, ImageStat, ImageDraw


def main():
    out = ROOT / ".verify-semantics"
    out.mkdir(exist_ok=True)
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    data = json.loads((ROOT / "examples/semantic-scenes/scenes.json").read_text())
    scenes = []
    cursor = 0
    for raw in data["scenes"]:
        s = Scene.model_validate(raw)
        s.start_frame = cursor
        cursor += s.frames
        compile_motion(s, [], 30, allow_estimated=True)
        scenes.append(s)
    board = StoryboardIR(
        title="语义场景固定验证",
        language="zh-CN",
        audience="general",
        scenes=scenes,
        total_frames=cursor,
    )
    w = Workspace(out / "engineering")
    w.prepare({**board.model_dump(),"motion_review_required":True}, media)
    receipt = request_assets(
        w,
        [
            AssetRequirement(
                id="knowledge",
                purpose="为检索解释制作文档素材",
                title="交付检查清单",
                items=[
                    dict(
                        text="先核对当前关键阻塞",
                        detail="第 2 节：检查恢复时间与后续依赖",
                        active=True,
                    ),
                    dict(text="引用依据后再给结论", detail="保持风险与事实区分"),
                ],
            )
        ],
        lambda: None,
    )
    source = (ROOT / "examples/semantic-scenes/Video.tsx").read_text()
    w.edit([SourceEdit(path="src/Video.tsx", content=source)])
    modules = w.project / "node_modules"
    if not modules.exists():
        modules.symlink_to(ROOT / "node_modules", target_is_directory=True)
    stamp = w.fingerprint()
    runner = Runner()
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
            timeout=900,
            env=os.environ.copy(),
        )
        result = read_receipt(target / "result.json", action)
        if action == "preview":
            for clip in result["clips"]:
                raw_scene = next(s.model_dump() for s in scenes if s.id == clip["scene_id"])
                metadata = json.loads(runner.run([
                    "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                    target / clip["name"],
                ]))
                validate_motion_clip(clip, raw_scene, metadata, board.fps)
        assert result["ok"]
        assert w.fingerprint() == stamp
    props = json.loads((w.project / "props.json").read_text())
    compat = out / "compatibility"
    compat.mkdir(exist_ok=True)
    shutil.copytree(w.project / "public", compat / "public", dirs_exist_ok=True)
    # Same scenes at native 4K, not a resized 1080p movie.
    props.update(width=3840, height=2160)
    (compat / "props.json").write_text(json.dumps(props, ensure_ascii=False))
    runner.run(
        ["node", ROOT / "packages/video/render.mjs", compat],
        timeout=900,
        env=os.environ.copy(),
    )
    report = {
        "fixture": data["authorship"],
        "source_hash": stamp,
        "semantic_renderer_sha256": hashlib.sha256(
            (ROOT / "packages/engineering-template/src/semantic-kit.tsx").read_bytes()
        ).hexdigest(),
        "engineering": inspect_video(out / "final/video.mp4", runner, cursor),
        "compatibility": inspect_video(
            compat / "video.mp4", runner, cursor, 3840, 2160
        ),
        "asset_receipt": receipt,
        "measured_tts": False,
        "full_human_listening": False,
    }
    samples = []
    for name, frame in [
        ("before", 0),
        ("tool-result", 150),
        ("confirmed", 220),
        ("rag-answer", scenes[1].start_frame + 160),
        ("last", cursor - 1),
    ]:
        file = out / (name + ".png")
        runner.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                str(frame / 30),
                "-i",
                out / "final/video.mp4",
                "-frames:v",
                "1",
                file,
            ]
        )
        samples.append(file)
    a = Image.open(samples[0]).convert("RGB").crop((800, 320, 1340, 740))
    b = Image.open(samples[1]).convert("RGB").crop((800, 320, 1340, 740))
    difference = ImageStat.Stat(ImageChops.difference(a, b)).mean
    assert max(difference) > 2
    report["tool_result_pixel_difference"] = difference
    preview = json.loads((out / "preview/result.json").read_text())
    last = next(e for e in scenes[0].compiled_semantic_events if e.id == "confirm")
    assert any(
        c["scene_id"] == "agent"
        and c["start_frame"] < last.start_frame
        and c["end_frame"] > last.end_frame
        for c in preview["clips"]
    )
    report["late_confirmation_preview"] = "covered"
    report["continuous_clips"] = len(preview["clips"])
    report["clip_metadata_vs_declared_ranges"] = "all passed"
    sheet = Image.new("RGB", (1920, 720), "#e4ece7")
    for i, path in enumerate(samples):
        im = Image.open(path).convert("RGB")
        im.thumbnail((640, 360))
        sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
    sheet.save(out / "review.jpg", quality=93)
    (ROOT / "docs/verification-semantic-scenes.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
