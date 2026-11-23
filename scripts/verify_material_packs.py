"""Compile/render ONLY reviewed repository material fixtures; no source/path arguments.

Exercises real selection, receipts, offline renderer, source hashes and export; no model/TTS.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    if len(sys.argv) != 1:
        raise SystemExit("Fixed verification accepts no arguments")
    from explainer.domain import Scene, StoryboardIR
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.contracts import SourceEdit
    from explainer.services.material_staging import (
        stage_materials,
        verify_staged_materials,
    )
    from explainer.services.assets.registry import request_assets
    from explainer.services.assets.usage import asset_usage
    from explainer.services.materials import material_library
    from explainer.services.process import Runner
    from explainer.services.engineering.tools import read_receipt
    from explainer.services.quality import inspect_video
    from PIL import Image, ImageChops, ImageStat

    out = ROOT / ".verify-material-packs"
    media = out / "media"
    media.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    library = material_library()
    entries = [m for m in library["items"] if m.get("pack_id")]
    assert len(entries) == 14
    groups = [entries[:8], entries[8:11], entries[11:13], entries[13:]]
    scenes = []
    for i, group in enumerate(groups):
        elements = []
        for m in group:
            key = m["id"].split(".")[-1]
            elements.append(
                dict(
                    id=key,
                    role="subject",
                    description=m["purpose"],
                    implementation="kit" if m["asset_type"] == "component" else "asset",
                    **(
                        {"library_ref": f"library:{m['id']}@{m['version']}"}
                        if m["asset_type"] == "component"
                        else {"asset_key": key}
                    ),
                )
            )
        scenes.append(
            Scene(
                id=f"pack-{i}",
                type="cards",
                title=[
                    "可识别的对象",
                    "日常生活的隐喻",
                    "文字也能有节奏",
                    "观察一个具体物体",
                ][i],
                narration="让具体的对象帮助我们理解。",
                frames=120,
                start_frame=i * 120,
                creation=dict(
                    visual_goal="通过可辨认对象和实际帧变化验证精选素材在真实工程中的使用",
                    composition="围绕主要对象构图，保持中文标题和对象可见，避免遮挡",
                    palette=["#faf3e4", "#244856"],
                    techniques=["three" if i == 3 else "images" if i == 1 else "svg"],
                    scene_source="src/Video.tsx",
                    elements=elements,
                ),
            )
        )
    board = StoryboardIR(
        title="让知识变得可见",
        language="zh-CN",
        audience="general",
        scenes=scenes,
        total_frames=480,
        design_pack="editorial_warm",
    )
    w = Workspace(out / "engineering")
    w.prepare({**board.model_dump(), "motion_review_required": True}, media)
    selection = stage_materials(
        w, [f"library:{m['id']}@{m['version']}" for m in entries]
    )
    requirements = [
        dict(
            id=m["id"].split(".")[-1] if m["asset_type"] == "image" else "avocado",
            provider="library_asset",
            library_ref=f"library:{m['id']}@{m['version']}",
            title=m["name"],
            purpose=m["purpose"],
        )
        for m in entries
        if m["asset_type"] != "component"
    ]
    # The model's registered key is avocado, not the catalog's generic suffix 'model'.
    props = json.loads((w.project / "props.json").read_text())
    props["scenes"][3]["creation"]["elements"][0]["asset_key"] = "avocado"
    (w.project / "props.json").write_text(
        json.dumps(props, ensure_ascii=False, indent=2)
    )
    request_assets(w, requirements, lambda: None)
    w.edit(
        [
            SourceEdit(
                path="src/Video.tsx",
                content=(ROOT / "examples/material-packs/Video.tsx").read_text(),
            )
        ]
    )
    if not (w.project / "node_modules").exists():
        (w.project / "node_modules").symlink_to(
            ROOT / "node_modules", target_is_directory=True
        )
    verify_staged_materials(w)
    stamp = w.fingerprint()
    runner = Runner()
    for action in ("build", "preview", "final"):
        print(f"material packs: {action}", flush=True)
        runner.run(
            [
                "node",
                ROOT / "packages/engineering-template/render.mjs",
                w.project,
                action,
                out / action,
            ],
            timeout=1800,
            env=os.environ.copy(),
        )
        assert read_receipt(out / action / "result.json", action)["ok"]
        assert w.fingerprint() == stamp
        if action == "preview":
            # Check the MODEL region in every model still, not only changing text elsewhere.
            for frame in (372, 414, 462, 479):
                im = Image.open(out / "preview" / f"frame-{frame:06d}.png").convert(
                    "RGB"
                )
                variance = sum(ImageStat.Stat(im.crop((250, 340, 900, 950))).var)
                assert variance > 100, ("blank model still", frame, variance)
    video = out / "final/video.mp4"
    metadata = inspect_video(video, runner, 480)
    runner.run(["ffmpeg", "-v", "error", "-i", video, "-f", "null", "-"], timeout=120)
    changes = {}
    sheet = Image.new("RGB", (1920, 540), "#f5efde")
    for i in range(4):
        pair = []
        for j, local in enumerate((12, 102)):
            frame = i * 120 + local
            target = out / f"evidence-{frame}.png"
            runner.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    str(frame / 30),
                    "-i",
                    video,
                    "-frames:v",
                    "1",
                    target,
                ]
            )
            im = Image.open(target).convert("RGB")
            pair.append(im.crop((100, 280, 1820, 960)))
            im.thumbnail((480, 270))
            sheet.paste(im, (i * 480, j * 270))
        delta = sum(ImageStat.Stat(ImageChops.difference(*pair)).mean)
        assert delta > 0.5, (i, delta)
        changes[scenes[i].id] = delta
    sheet.save(out / "review.jpg", quality=94)
    w.export(out / "Material_Packs_Project.zip", dict(shots=[]))
    report = dict(
        materials=14,
        packs=4,
        source_hash=stamp,
        selection=selection,
        assets=list(asset_usage(json.loads((w.project / "props.json").read_text()))),
        media=metadata,
        seconds=16,
        frames=480,
        video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
        pixel_changes=changes,
        native_inference=False,
        image_model_inference=False,
        audio="none",
        timing="estimated_draft",
        human_full_playback_and_listening=False,
    )
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (ROOT / "docs/verification-material-packs.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            dict(
                materials=14,
                packs=4,
                seconds=16,
                source_hash=stamp,
                pixel_changes=changes,
            )
        )
    )


if __name__ == "__main__":
    main()
