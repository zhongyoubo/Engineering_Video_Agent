"""Build/render the fixed self-project showcase, never arbitrary uploaded source.

Inputs: actual UI capture and explicitly prepared narration. Output is not a
native-model integration acceptance; no production sandbox policy is relaxed.
"""

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def captions(words, transcript):
    cues, chunk, position = [], [], 0
    for item in words:
        count = len(re.sub(r"[\W_]+", "", item["text"]))
        start, found = position, 0
        while position < len(transcript) and found < count:
            found += int(transcript[position].isalnum())
            position += 1
        while position < len(transcript) and not transcript[position].isalnum():
            position += 1
        word = {**item, "text": transcript[start:position]}
        chunk.append(word)
        text = "".join(w["text"] for w in chunk)
        if len(text) >= 24 or text.endswith(("。", "；", "，", ".")):
            cues.append(
                {"start": chunk[0]["start"], "end": chunk[-1]["end"], "text": text}
            )
            chunk = []
    if chunk:
        cues.append(
            {
                "start": chunk[0]["start"],
                "end": chunk[-1]["end"],
                "text": "".join(w["text"] for w in chunk),
            }
        )
    return cues


def main():
    from explainer.domain import Scene, StoryboardIR, Cue
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.contracts import SourceEdit
    from explainer.services.motion import compile_motion
    from explainer.services.process import Runner
    from explainer.services.quality import inspect_video
    from explainer.services.engineering.tools import inspect_frame
    from explainer.services.audio_analysis import waveform
    from explainer.adapters.alignment import validate_words

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action",
        choices=["all", "build", "preview", "final", "package"],
        default="all",
    )
    args = parser.parse_args()
    out = ROOT / ".verify-project-intro"
    audio = json.loads((out / "audio.json").read_text())
    ui = json.loads((out / "ui/evidence.json").read_text())
    story = json.loads((ROOT / "examples/project-intro/story.json").read_text())
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    shutil.copyfile(out / "ui/01-input.png", media / "input.png")
    shutil.copyfile(out / "ui/workbench.webm", media / "workbench.webm")
    specs = {
        "intro": (
            "code_scan",
            ["源码 / 提示词", "内容策划与分镜", "编译与图像审查", "视频与完整源码"],
            ["项目源码", "内容策划", "构建", "交付"],
        ),
        "visual": (
            "overview",
            [
                "代码扫描",
                "关系网络",
                "容量变化",
                "队列瓶颈",
                "方案对比",
                "持续深入",
                "内容总览",
            ],
            ["Agent"] * 7,
        ),
        "gates": (
            "overview",
            ["编译", "试渲染", "检查", "交付"],
            ["构建", "预览", "审查", "最终渲染"],
        ),
    }
    scenes, waves, cursor = [], {}, 0
    srt = []
    for item in story:
        recording = audio[item["id"]]
        words = validate_words(
            recording["words"], item["narration"], recording["duration"]
        )
        path = Path(recording["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != recording["sha256"]:
            raise RuntimeError("Audio checksum changed")
        shutil.copyfile(path, media / (item["id"] + ".wav"))
        measurement = waveform(path)
        assert not measurement["silent"]
        waves[item["id"]] = measurement["peaks"]
        # Preserve all speech at its actual rate; a short final hold never cuts a word.
        frames = math.ceil(recording["duration"] * 30) + (
            45 if item["id"] == "boundary" else 24
        )
        scene = Scene(
            **item,
            type="flow",
            duration=frames / 30,
            start_frame=cursor,
            frames=frames,
            code="// Engineering_Video_Agent / real source modules\napps/api/src/explainer/\n  services/engineering/agent.py\n  services/engineering/controller.py\n  services/motion.py\n  adapters/voice.py\n\npackages/engineering-template/\n  src/motion-kit.tsx\n  render.mjs\n\napps/studio/src/ProductionInspector.tsx",
        )
        scene.cues = [Cue(**c) for c in captions(words, scene.narration)]
        if scene.id in specs:
            pattern, labels, anchors = specs[scene.id]
            scene.motion = {
                "purpose": "依据实际旁白编排固定项目介绍镜头",
                "pattern": pattern,
                "layout": "fan" if scene.id == "visual" else "grid",
                "elements": [
                    {
                        "id": f"gate{i}" if scene.id == "gates" else f"e{i}",
                        "label": label,
                    }
                    for i, label in enumerate(labels)
                ],
                "events": [
                    {
                        "id": f"cue{i}",
                        "target": f"gate{i}" if scene.id == "gates" else f"e{i}",
                        "action": "reveal",
                        "anchor": {
                            "phrase": anchors[i],
                            "offset_ms": i * 120 if scene.id == "visual" else 0,
                        },
                        "duration_ms": 400,
                    }
                    for i in range(len(labels))
                ],
            }
            # Assignment validation is enabled by the domain model only on construction.
            from explainer.specs import SceneSpec

            scene.motion = SceneSpec.model_validate(scene.motion)
            compile_motion(scene, words, 30)
        values = scene.model_dump()
        values["audio_src"] = scene.id + ".wav"
        scenes.append(values)
        for cue in scene.cues:
            srt.append((cursor / 30 + cue.start, cursor / 30 + cue.end, cue.text))
        cursor += frames
    board = StoryboardIR(
        title="Engineering Video Agent · 项目介绍与实测",
        language="zh-CN",
        audience="developer",
        scenes=[{k: v for k, v in s.items() if k != "audio_src"} for s in scenes],
        width=3840,
        height=2160,
        total_frames=cursor,
        design_pack="editorial_warm",
        audio_alignment="native_words",
    )
    # audio_src is a render-only field and must not be discarded by domain serialization.
    props = {
        **board.model_dump(),
        "scenes": scenes,
        "motion_review_required": True,
        "intro_meta": {
            "waveforms": waves,
            "source_files": ui["revision"]["content"]["files_count"],
            "recording_start": 0,
        },
    }
    workspace = Workspace(out / "session")
    workspace.prepare(props, media)
    source = (ROOT / "examples/project-intro/Video.tsx").read_text()
    workspace.edit([SourceEdit(path="src/Video.tsx", content=source)])
    link = workspace.project / "node_modules"
    if not link.exists():
        link.symlink_to(ROOT / "node_modules", target_is_directory=True)
    runner = Runner()
    actions = (
        ["build", "preview", "final"]
        if args.action == "all"
        else []
        if args.action == "package"
        else [args.action]
    )
    for action in actions:
        target = out / action
        target.mkdir(exist_ok=True)
        assert workspace.state["files"] == {"src/Video.tsx": source}
        runner.run(
            [
                "node",
                ROOT / "packages/engineering-template/render.mjs",
                workspace.project,
                action,
                target,
            ],
            timeout=1800,
            env=os.environ.copy(),
        )
        receipt = json.loads((target / "result.json").read_text())
        if not receipt.get("ok"):
            raise RuntimeError(receipt)
        (target / "source-hash.txt").write_text(workspace.fingerprint())
        print(
            f"{action}: passed / {cursor} frames / source {workspace.fingerprint()[:12]}",
            flush=True,
        )
        if action == "preview":
            for frame in receipt["frames"]:
                inspect_frame(target / frame["name"], 3840, 2160)
    if args.action not in {"all", "package"}:
        return
    for action in ["build", "preview", "final"]:
        if (out / action / "source-hash.txt").read_text() != workspace.fingerprint():
            raise RuntimeError("Stale build/preview/final evidence")
    metadata = inspect_video(out / "final/video.mp4", runner, cursor, 3840, 2160)
    workspace.export(
        out / "remotion-project.zip",
        {
            "authored_fixture": True,
            "native_inference": False,
            "narration_source": "public README at 8973bcade2f342eda2a082024ff73c4904b722e5",
            "voice": "Edge zh-CN-YunxiNeural",
            "source_files": props["intro_meta"]["source_files"],
        },
    )

    def stamp(t):
        ms = round(t * 1000)
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    (out / "captions.srt").write_text(
        "\n\n".join(
            f"{i + 1}\n{stamp(a)} --> {stamp(b)}\n{text}"
            for i, (a, b, text) in enumerate(srt)
        )
        + "\n"
    )
    (out / "script.md").write_text(
        "# Engineering Video Agent · 项目介绍\n\n"
        + "\n\n".join(
            f"## {i + 1}. {s['title']}\n\n{s['narration']}"
            for i, s in enumerate(scenes)
        )
    )
    report = {
        "media": metadata,
        "actual_source_ingestion_files": props["intro_meta"]["source_files"],
        "source_zip_sha256": hashlib.sha256(
            (out / "source.zip").read_bytes()
        ).hexdigest(),
        "source_hash": workspace.fingerprint(),
        "voice": "Edge zh-CN-YunxiNeural",
        "measured_timing": "native word boundaries; not Whisper",
        "measured_audio_seconds": sum(v["duration"] for v in audio.values()),
        "native_model_inference": False,
        "isolated_generated_source_execution": False,
        "fixed_authored_project": True,
        "full_human_listening_review": False,
        "preview_frames": 21,
        "continuous_clips": 7,
    }
    (out / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
