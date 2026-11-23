"""Render ONLY fixed platform spatial components/data and the existing fixed dispatcher.

No user paths, plans, code or media arguments. City stills are actual platform-rendered
assets registered through project image tools; not image-model or native-Agent inference.
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
    from fastapi.testclient import TestClient
    from explainer.api import app
    from explainer.config import Settings, get_settings
    from explainer.db import Database
    from explainer.domain import Scene, StoryboardIR
    from explainer.services.assets.project_images import resolve_image
    from explainer.services.assets.usage import asset_usage
    from explainer.services.engineering.contracts import EngineeringAction, SourceEdit
    from explainer.services.engineering.controller import EngineeringController
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.tools import read_receipt, validate_motion_clip
    from explainer.services.motion import compile_motion
    from explainer.services.process import Runner
    from explainer.services.quality import inspect_video
    from explainer.storage import Storage
    from PIL import Image, ImageChops, ImageStat

    out = ROOT / ".verify-spatial-scenes"
    out.mkdir(exist_ok=True)
    media = out / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", media / "noto.otf")
    scenes = []
    cursor = 0
    for raw in json.loads(
        (ROOT / "examples/spatial-storytelling/scenes.json").read_text()
    )["scenes"]:
        scene = Scene.model_validate(raw)
        scene.start_frame = cursor
        cursor += scene.frames
        compile_motion(scene, [], 30, allow_estimated=True)
        scenes.append(scene)
    runner = Runner()
    source = (ROOT / "examples/reference-mechanisms/Video.tsx").read_text()

    def prepare(name, selected):
        board = StoryboardIR(
            title="把复杂的信息变得可见",
            language="zh-CN",
            audience="general",
            scenes=selected,
            total_frames=sum(s.frames for s in selected),
            design_pack="neon_horizon",
        )
        w = Workspace(out / name)
        # The city-only pass produces artwork stills; continuous clips are checked in the full pass.
        w.prepare({**board.model_dump(), "motion_review_required": len(selected) > 1}, media)
        w.edit([SourceEdit(path="src/Video.tsx", content=source)])
        if not (w.project / "node_modules").exists():
            (w.project / "node_modules").symlink_to(
                ROOT / "node_modules", target_is_directory=True
            )
        return w, board

    def execute(w, action, target):
        print(f"spatial {action}: {target.name}", flush=True)
        runner.run(
            [
                "node",
                ROOT / "packages/engineering-template/render.mjs",
                w.project,
                action,
                target,
            ],
            timeout=1800,
            env=os.environ.copy(),
        )
        result = read_receipt(target / "result.json", action)
        assert result["ok"]
        return result

    # Hardcoded trusted platform renderer makes its own city artwork; no borrowed reference frames.
    city, _ = prepare("city-project", scenes[:1])
    preview = execute(city, "preview", out / "city-preview")
    assert preview["font_required"] is True
    stills = [out / "city-preview" / f"frame-{f:06d}.png" for f in (21, 94, 178)]
    assert all(p.is_file() for p in stills)
    assert len({hashlib.sha256(p.read_bytes()).hexdigest() for p in stills}) == 3
    artwork = []
    for i, path in enumerate(stills, 1):
        clean = out / f"city-artwork-{i}.png"
        Image.open(path).convert("RGB").crop((350, 280, 1760, 920)).save(clean)
        artwork.append(clean)
    settings = Settings(
        data_dir=out / "data", api_token="fixed-spatial-fixture-token-20261123"
    ).prepare()
    app.dependency_overrides[get_settings] = lambda: settings
    requests = []
    try:
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer " + settings.api_token}
            project = client.post(
                "/api/v1/projects", headers=headers, json={"name": "空间叙事固定验证"}
            ).json()["id"]
            for i, path in enumerate(artwork, 1):
                response = client.post(
                    f"/api/v3/projects/{project}/images",
                    headers=headers,
                    data={"title": f"原创程序城市视角{i}"},
                    files={
                        "file": (f"city-view-{i}.png", path.read_bytes(), "image/png")
                    },
                )
                assert response.status_code == 201, response.text
                requests.append(
                    dict(
                        id=f"city-view-{i}",
                        provider="project_image",
                        project_asset_id=response.json()["id"],
                        title=f"城市视角{i}",
                        purpose="复用同一原创城市场景的真实渲染画面，整理成可比较的数量矩阵",
                    )
                )
    finally:
        app.dependency_overrides.clear()
    db = Database(settings.data_dir)
    store = Storage(settings, db)
    tenant = db.one("SELECT tenant FROM projects WHERE id=?", (project,))["tenant"]
    w, board = prepare("engineering", scenes)
    controller = EngineeringController(
        w,
        None,
        None,
        lambda _: None,
        lambda *a: None,
        lambda: None,
        resolve_image=lambda id: resolve_image(db, store, tenant, project, id),
    )
    controller.apply(
        EngineeringAction(
            action="request_assets",
            summary="导入固定平台原创城市画面",
            files=[],
            review=None,
            asset_requests=requests,
        )
    )
    stamp = w.fingerprint()
    for action in ("build", "preview", "final"):
        result = execute(w, action, out / action)
        assert stamp == w.fingerprint()
        if action == "preview":
            for clip in result["clips"]:
                scene = next(s for s in scenes if s.id == clip["scene_id"])
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
                            out / action / clip["name"],
                        ]
                    )
                )
                validate_motion_clip(clip, scene.model_dump(), metadata, 30)
    video = out / "final/video.mp4"
    metadata = inspect_video(video, runner, board.total_frames)
    runner.run(["ffmpeg", "-v", "error", "-i", video, "-f", "null", "-"], timeout=120)
    changes = {}
    for index, (a, b) in enumerate(((30, 180), (240, 400), (450, 600), (655, 810))):
        files = []
        for frame in (a, b):
            path = out / f"evidence-{frame}.png"
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
                    path,
                ]
            )
            files.append(path)
        before = Image.open(files[0]).convert("RGB").crop((100, 260, 1820, 880))
        after = Image.open(files[1]).convert("RGB").crop((100, 260, 1820, 880))
        delta = sum(ImageStat.Stat(ImageChops.difference(before, after)).mean)
        assert delta > 1, (index, delta)
        changes[scenes[index].id] = delta
    sheet = Image.new("RGB", (1920, 540), "#101326")
    for i, frame in enumerate((30, 180, 240, 400, 450, 600, 655, 810)):
        im = Image.open(out / f"evidence-{frame}.png").convert("RGB")
        im.thumbnail((480, 270))
        sheet.paste(im, ((i % 4) * 480, (i // 4) * 270))
    sheet.save(out / "review.jpg", quality=94)
    props = json.loads((w.project / "props.json").read_text())
    uses = asset_usage(props)
    assert set(uses) == {
        "quantity:city-view-1",
        "quantity:city-view-2",
        "quantity:city-view-3",
    }
    report = dict(
        source_hash=stamp,
        video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
        media=metadata,
        scenes=len(scenes),
        frames=board.total_frames,
        seconds=board.total_frames / 30,
        per_scene_pixel_difference=changes,
        assets=list(uses),
        city_still_hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in stills],
        registered_artwork_hashes=[
            hashlib.sha256(p.read_bytes()).hexdigest() for p in artwork
        ],
        gl="swangle",
        native_inference=False,
        image_model_inference=False,
        audio="none",
        timing="estimated_draft",
        human_playback_and_listening=False,
        isolation="fixed platform verifier only; no Docker deployment claim",
        note="original geometry and rendered stills; no reference-video image or audio reused",
    )
    w.export(
        out / "Spatial_Storytelling_Project.zip", {"fixed_fixture": True, **report}
    )
    (out / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (ROOT / "docs/verification-spatial-scenes.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
