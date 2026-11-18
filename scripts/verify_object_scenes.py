"""Render ONLY fixed platform-authored object fixtures, never user/generated TSX.

Actual object-state pixel changes and quiet Foley in both render paths. Draft authored
anchor timing is explicitly not TTS, native inference, hardware or listening acceptance.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.domain import Brief, Scene, StoryboardIR
from explainer.services.editorial import prepare_presentation
from explainer.services.motion import compile_motion
from explainer.services.visuals import prepare_visual_assets
from explainer.services.process import Runner
from explainer.services.quality import inspect_video
from explainer.services.audio_analysis import waveform
from explainer.services.engineering.workspace import Workspace
from explainer.services.engineering.contracts import SourceEdit
from PIL import Image, ImageChops, ImageStat


def main():
    out = ROOT / ".verify-objects"
    out.mkdir(exist_ok=True)
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    reference = json.loads((ROOT / "examples/object-scenes/hdmi.json").read_text())
    spec = reference["scenes"][1]["visual_scene"]
    spec["setting"] = "studio"
    spec["objects"][0]["label"] = "播放设备"
    spec["events"] = [
        dict(
            id="plug",
            target="hdmi",
            action="connect",
            anchor=dict(phrase="连接设备"),
            duration_ms=500,
            sound="connect",
        ),
        dict(
            id="power",
            target="tv",
            action="power_on",
            anchor=dict(phrase="连接设备"),
            duration_ms=500,
        ),
        dict(
            id="picture",
            target="hdmi",
            action="signal",
            anchor=dict(phrase="播放画面"),
            duration_ms=1800,
            channel="video",
            depends_on=["plug"],
        ),
        dict(
            id="play",
            target="tv",
            action="play",
            anchor=dict(phrase="播放画面"),
            duration_ms=500,
            depends_on=["power"],
        ),
        dict(
            id="sound",
            target="tv",
            action="sound",
            anchor=dict(phrase="发出声音"),
            duration_ms=600,
            sound="notify",
        ),
    ]
    first = Scene(
        id="connection",
        type="ui",
        title="连接设备，让画面和声音出现",
        narration="先连接设备，再播放画面，最后发出声音。",
        duration=5,
        frames=150,
        visual_scene=spec,
    )
    compile_motion(first, [], 30, allow_estimated=True)
    gallery = []
    kinds = [
        ("monitor", "显示器"),
        ("laptop", "笔记本"),
        ("phone", "手机"),
        ("player", "播放器"),
        ("router", "路由器"),
        ("server", "服务器"),
    ]
    for i, (kind, label) in enumerate(kinds):
        gallery.append(
            dict(
                id=kind,
                kind=kind,
                label=label,
                x=100 + (i % 3) * 530,
                y=15 + (i // 3) * 280,
                width=280,
                height=175,
            )
        )
    second = Scene(
        id="gallery",
        type="ui",
        title="同一对象层也可组合其他场景",
        narration="这些是对象库示例，不代表真实硬件测试。",
        frames=60,
        duration=2,
        start_frame=150,
        visual_scene=dict(purpose="检查非 HDMI 对象的识别与组合", objects=gallery),
    )
    third = Scene(
        id="audio",
        type="ui",
        title="音响和操作对象",
        narration="这是对象造型检查。",
        frames=60,
        duration=2,
        start_frame=210,
        visual_scene=dict(
            purpose="检查音频与交互对象的造型",
            objects=[
                dict(
                    id="bar",
                    kind="soundbar",
                    label="回音壁",
                    x=100,
                    y=250,
                    width=520,
                    height=100,
                ),
                dict(
                    id="speaker",
                    kind="speaker",
                    label="音箱",
                    x=820,
                    y=80,
                    width=200,
                    height=360,
                ),
                dict(
                    id="remote",
                    kind="remote",
                    label="遥控器",
                    x=1350,
                    y=100,
                    width=125,
                    height=330,
                ),
            ],
        ),
    )
    third.visual_scene.sound_enabled = True
    from explainer.visual_scene import ObjectEvent

    third.visual_scene.events = [
        ObjectEvent(
            id="click",
            target="remote",
            action="press",
            anchor={"phrase": "造型"},
            duration_ms=300,
            sound="click",
        )
    ]
    compile_motion(third, [], 30, allow_estimated=True)
    board = StoryboardIR(
        title="对象场景固定检查",
        language="zh-CN",
        audience="general",
        scenes=[first, second, third],
        total_frames=270,
    )
    prepare_presentation(
        board,
        Brief(
            title=board.title,
            prompt="固定对象场景协议检查",
            voice="none",
            quality_profile="draft",
        ),
    )
    prepare_visual_assets(board, media)
    props = board.model_dump()
    compatibility = out / "compatibility"
    compatibility.mkdir(exist_ok=True)
    shutil.copytree(media, compatibility / "public", dirs_exist_ok=True)
    (compatibility / "props.json").write_text(json.dumps(props, ensure_ascii=False))
    runner = Runner()
    runner.run(
        ["node", ROOT / "packages/video/render.mjs", compatibility],
        env=os.environ.copy(),
        timeout=600,
    )
    result = {"compatibility": inspect_video(compatibility / "video.mp4", runner, 270)}
    workspace = Workspace(out / "engineering")
    workspace.prepare(props, media)
    source = (ROOT / "examples/object-scenes/Video.tsx").read_text()
    workspace.edit([SourceEdit(path="src/Video.tsx", content=source)])
    modules = workspace.project / "node_modules"
    if not modules.exists():
        modules.symlink_to(ROOT / "node_modules", target_is_directory=True)
    stamp = workspace.fingerprint()
    assert workspace.state["files"] == {"src/Video.tsx": source}
    engineering = out / "engineering-output"
    engineering.mkdir(exist_ok=True)
    runner.run(
        [
            "node",
            ROOT / "packages/engineering-template/render.mjs",
            workspace.project,
            "build",
            engineering,
        ],
        env=os.environ.copy(),
        timeout=180,
    )
    assert json.loads((engineering / "result.json").read_text())["ok"]
    runner.run(
        [
            "node",
            ROOT / "packages/engineering-template/render.mjs",
            workspace.project,
            "final",
            engineering,
        ],
        env=os.environ.copy(),
        timeout=600,
    )
    assert (
        json.loads((engineering / "result.json").read_text())["ok"]
        and workspace.fingerprint() == stamp
    )
    result["engineering"] = inspect_video(engineering / "video.mp4", runner, 270)
    for path in [compatibility, engineering]:
        for name, frame in [("before", 0), ("after", 100)]:
            runner.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    str(frame / 30),
                    "-i",
                    path / "video.mp4",
                    "-frames:v",
                    "1",
                    path / (name + ".png"),
                ]
            )
        a = Image.open(path / "before.png").convert("RGB").crop((1045, 282, 1670, 525))
        b = Image.open(path / "after.png").convert("RGB").crop((1045, 282, 1670, 525))
        change = ImageStat.Stat(ImageChops.difference(a, b)).mean
        assert min(change) > 10, "Black display must become a visible picture"
        runner.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                path / "video.mp4",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                path / "foley.wav",
            ]
        )
        actual = waveform(path / "foley.wav")
        assert not actual["silent"] and -45 < actual["peak_dbfs"] < -14, (
            "Actual quiet Foley must be mixed, not just declared"
        )
        result[path.name + "-change"] = {
            "screen_mean_rgb_difference": change,
            "foley_peak_dbfs": actual["peak_dbfs"],
        }
    result.update(
        fixture="fixed platform-authored objects; estimated draft anchor timing; no TTS/native inference/hardware measurements",
        objects=11,
        source_hash=stamp,
        renderer_sha256=hashlib.sha256(
            (ROOT / "packages/engineering-template/src/scene-objects.tsx").read_bytes()
        ).hexdigest(),
        human_full_playback_listening=False,
    )
    (ROOT / "docs/verification-object-scenes.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
