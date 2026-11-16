"""Render authored cover/outro and assemble the hash-verified previous body.

No new TTS, model call or arbitrary generated-code host execution is performed.
The body remains an explicit media asset; its original editable source is delivered.
"""

import hashlib
import math
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from explainer.domain import Scene, StoryboardIR
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.contracts import SourceEdit
    from explainer.services.engineering.tools import inspect_frame
    from explainer.services.process import Runner
    from explainer.services.quality import inspect_video

    old = ROOT / ".verify-project-intro"
    out = ROOT / ".verify-bookends"
    out.mkdir(exist_ok=True)
    previous = json.loads((old / "verification.json").read_text())
    body = old / "final/video.mp4"
    body_sha = hashlib.sha256(body.read_bytes()).hexdigest()
    if body_sha != previous["video_sha256"] or previous["media"]["frames"] != 1927:
        raise RuntimeError("Body differs from the previously verified introduction")
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(body, media / "body.mp4")
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    definitions = [
        ("cover", "工程视频智能体", 90),
        ("body", "项目介绍正文", 1927),
        ("outro", "让复杂内容，清楚呈现", 120),
    ]
    scenes, cursor = [], 0
    for key, title, frames in definitions:
        scene = Scene(
            id=key,
            type="title" if key != "body" else "ui",
            title=title,
            narration="无新配音；正文保留原有 Edge 旁白。",
            start_frame=cursor,
            frames=frames,
            duration=frames / 30,
        )
        scenes.append(scene)
        cursor += frames
    board = StoryboardIR(
        title="Engineering Video Agent · 封面与结尾修订",
        language="zh-CN",
        audience="developer",
        width=3840,
        height=2160,
        scenes=scenes,
        total_frames=cursor,
        design_pack="editorial_warm",
    )
    w = Workspace(out / "session")
    w.prepare(board.model_dump(), media)
    source = (ROOT / "examples/project-intro/Bookends.tsx").read_text()
    w.edit([SourceEdit(path="src/Video.tsx", content=source)])
    link = w.project / "node_modules"
    if not link.exists():
        link.symlink_to(ROOT / "node_modules", target_is_directory=True)
    source_hash = w.fingerprint()
    runner = Runner()
    render = out / "render"
    render.mkdir(exist_ok=True)
    assert w.state["files"] == {"src/Video.tsx": source}
    runner.run(
        [
            "node",
            ROOT / "examples/project-intro/render-bookends.mjs",
            w.project,
            render,
        ],
        timeout=1200,
        env=os.environ.copy(),
        on_line=print,
    )
    receipt = json.loads((render / "result.json").read_text())
    assert receipt["ok"] and w.fingerprint() == source_hash
    for frame in receipt["frames"]:
        if frame != 2016:
            inspect_frame(render / f"frame-{frame}.png", 3840, 2160)
    # The final original-body frame is an intentional fade, not a content frame.
    # Compare all reused body samples pixel-by-pixel against the verified input,
    # including that transition. This also catches scaling/cropping or stale video.
    from PIL import Image, ImageChops, ImageStat

    runner.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            body,
            "-vf",
            "select=eq(n\\,50)+eq(n\\,986)+eq(n\\,1767)+eq(n\\,1926)",
            "-fps_mode",
            "vfr",
            out / "source-%02d.png",
        ],
        timeout=300,
    )
    pixel_checks = []
    for index, frame in enumerate([140, 1076, 1857, 2016], 1):
        expected = Image.open(out / f"source-{index:02d}.png").convert("RGB")
        actual = Image.open(render / f"frame-{frame}.png").convert("RGB")
        if actual.size != expected.size:
            raise RuntimeError("Reused body dimensions changed")
        diff = ImageChops.difference(expected, actual)
        rms = math.sqrt(sum(ImageStat.Stat(diff).sum2) / (3840 * 2160 * 3))
        if rms > 2.5:
            raise RuntimeError(f"Reused body pixels differ at {frame}: {rms}")
        pixel_checks.append(
            {"master_frame": frame, "source_frame": frame - 90, "rgb_rms": rms}
        )
    # Video-only streams have identical dimensions/rate and independent keyframe starts.
    segments = []
    for name, path, frames in [
        ("cover", render / "cover.mp4", 90),
        ("body", body, 1927),
        ("outro", render / "outro.mp4", 120),
    ]:
        target = out / (name + "-video.mp4")
        runner.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                path,
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                "-an",
                target,
            ]
        )
        segments.append(f"file '{target}'\nduration {frames / 30:.9f}")
    inputs = out / "segments.txt"
    inputs.write_text("\n".join(segments) + "\n")
    final = out / "video.mp4"
    runner.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            inputs,
            "-i",
            body,
            "-filter_complex",
            "[1:a]atrim=duration=64.233333333,asetpts=PTS-STARTPTS,adelay=3000:all=1,apad,atrim=duration=71.233333333[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            final,
        ],
        timeout=300,
    )
    measured = inspect_video(final, runner, 2137, 3840, 2160)
    level_log = runner.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            final,
            "-vn",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json",
            "-f",
            "null",
            "-",
        ],
        timeout=300,
    )
    levels = json.JSONDecoder().raw_decode(level_log[level_log.rfind("{") :])[0]
    plan = {
        "fixed_authored_assembly": True,
        "new_bookends": {"cover_seconds": 3, "outro_seconds": 4},
        "body_video_sha256": body_sha,
        "voice": "Existing Edge Yunxi audio retained; no new Ming/Qwen inference",
        "body_source_zip": "body-editable-project.zip",
    }
    w.export(out / "master-project.zip", plan)
    shutil.copyfile(render / "frame-0.png", out / "cover-4k.png")
    report = {
        "media": measured,
        "source_hash": source_hash,
        "video_sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
        "body_video_sha256": body_sha,
        "freshly_rendered_bookend_frames": 210,
        "reused_body_frames": 1927,
        "sampled_frames": receipt["frames"],
        "body_pixel_checks": pixel_checks,
        "voice": "Edge zh-CN-YunxiNeural (retained)",
        "new_tts_inference": False,
        "ming_inference": False,
        "full_human_listening_review": False,
        "audio": {
            "integrated_lufs": float(levels["input_i"]),
            "true_peak_dbtp": float(levels["input_tp"]),
        },
        "assembly": "Fresh Remotion bookends + hash-verified existing video body; no video re-encoding of the body",
    }
    (out / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
