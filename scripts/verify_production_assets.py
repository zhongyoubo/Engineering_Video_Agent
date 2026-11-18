"""Fixed, reviewed repository fixture ONLY; never accepts TSX, props or plans from users.

Reuses hash-pinned illustrations and Edge word-timed narration through authenticated project
imports, engineering asset tools, protected Remotion composition and actual compiler/render.
This is explicitly not native inference, new image inference or Docker deployment acceptance.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from fastapi.testclient import TestClient
    from explainer.api import app
    from explainer.config import Settings, get_settings
    from explainer.db import Database
    from explainer.domain import Scene, StoryboardIR
    from explainer.services.assets.project_images import resolve_image
    from explainer.services.engineering.contracts import EngineeringAction, SourceEdit
    from explainer.services.engineering.controller import EngineeringController
    from explainer.services.engineering.workspace import Workspace
    from explainer.services.engineering.tools import read_receipt, validate_motion_clip
    from explainer.services.motion import compile_motion
    from explainer.services.timeline import word_cues
    from explainer.services.process import Runner
    from explainer.services.quality import inspect_video
    from explainer.storage import Storage
    from PIL import Image, ImageChops, ImageStat

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-directory", type=Path, required=True)
    args = parser.parse_args()
    fixture = ROOT / "examples/illustrated-scenes"
    expected = json.loads((fixture / "media.manifest.json").read_text())
    for name, digest in expected.items():
        path = args.media_directory / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Fixed fixture input missing or changed: " + name)
    out = ROOT / ".verify-production-assets"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    settings = Settings(
        data_dir=out / "data", api_token="fixture-only-not-a-production-token"
    ).prepare()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            h = {"Authorization": "Bearer " + settings.api_token}
            project = client.post(
                "/api/v1/projects", headers=h, json={"name": "Agent 插画工程验证"}
            ).json()["id"]
            registered = {}
            for name in expected:
                if not name.startswith("assets/"):
                    continue
                path = args.media_directory / name
                response = client.post(
                    f"/api/v3/projects/{project}/images",
                    headers=h,
                    data={"title": path.stem},
                    files={"file": (path.name, path.read_bytes(), "image/png")},
                )
                assert response.status_code == 201, response.text
                registered[path.stem] = response.json()
    finally:
        app.dependency_overrides.clear()
    db = Database(settings.data_dir)
    store = Storage(settings, db)
    tenant = db.one("SELECT tenant FROM projects WHERE id=?", (project,))["tenant"]
    public = out / "media"
    public.mkdir()
    shutil.copyfile(
        ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf", public / "noto.otf"
    )
    scenes = []
    for data in json.loads((fixture / "scenes.json").read_text())["scenes"]:
        s = Scene.model_validate(data)
        audio = json.loads(
            (args.media_directory / "voice" / (s.id + ".json")).read_text()
        )
        compile_motion(s, audio["words"], 30)
        s.cues = word_cues(audio["words"], "zh-CN")
        shutil.copyfile(
            args.media_directory / "voice" / (s.id + ".wav"), public / (s.id + ".wav")
        )
        scenes.append(s)
    board = StoryboardIR(
        title="Agent，到底是什么？",
        language="zh-CN",
        audience="general",
        scenes=scenes,
        total_frames=sum(s.frames for s in scenes),
    )
    props = board.model_dump()
    props.update(
        width=1920,
        height=1080,
        motion_review_required=True,
        scenes=[{**s.model_dump(), "audio_src": s.id + ".wav"} for s in scenes],
    )
    w = Workspace(out / "engineering")
    w.prepare(props, public)
    controller = EngineeringController(
        w,
        None,
        None,
        lambda _: None,
        lambda *a: None,
        lambda: None,
        resolve_image=lambda id: resolve_image(db, store, tenant, project, id),
    )
    # Mediated action batch bound matches the native action contract (8).
    controller.apply(
        EngineeringAction(
            action="request_assets",
            summary="导入受检图片",
            files=[],
            review=None,
            asset_requests=[
                dict(
                    id=key,
                    purpose="复用已登记的具体场景和独立元素",
                    title=key,
                    provider="project_image",
                    project_asset_id=value["id"],
                    transparent=key in {"tomato", "greens"},
                )
                for key, value in registered.items()
            ],
        )
    )
    for key in registered:
        controller.apply(
            EngineeringAction(
                action="inspect_asset",
                summary="核对实际图片字节",
                files=[],
                review=None,
                asset_id=key,
            )
        )
    w.edit(
        [SourceEdit(path="src/Video.tsx", content=(fixture / "Video.tsx").read_text())]
    )
    (w.project / "node_modules").symlink_to(
        ROOT / "node_modules", target_is_directory=True
    )
    stamp = w.fingerprint()
    runner = Runner()
    receipts = {}
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
        receipts[action] = read_receipt(target / "result.json", action)
        assert receipts[action]["ok"] and stamp == w.fingerprint()
    for clip in receipts["preview"]["clips"]:
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
                    out / "preview" / clip["name"],
                ]
            )
        )
        validate_motion_clip(clip, scene, metadata, 30)
    # Actual causal frame differences; not a semantic-quality or listening claim.
    changes = []
    for s in scenes:
        for e in s.compiled_semantic_events:
            before = s.start_frame + max(0, e.start_frame - 1)
            after = s.start_frame + min(s.frames - 1, e.end_frame + 1)
            a = Image.open(out / "preview" / f"frame-{before:06}.png").convert("RGB")
            b = Image.open(out / "preview" / f"frame-{after:06}.png").convert("RGB")
            delta = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean)
            assert delta > 0.1
            changes.append(
                dict(
                    scene=s.id,
                    event=e.id,
                    before=before,
                    after=after,
                    pixel_difference=delta,
                )
            )
    archive = out / "Agent_Remotion_Project.zip"
    w.export(
        archive,
        {
            "fixture": "illustrated-scenes",
            "native_inference": False,
            "images": "registered imports",
        },
    )
    report = dict(
        source_hash=stamp,
        frames=board.total_frames,
        seconds=board.total_frames / 30,
        video=str(out / "final/video.mp4"),
        media=inspect_video(
            Path(str(out / "final/video.mp4")), runner, board.total_frames
        ),
        registered_images=len(registered),
        causal_changes=changes,
        compiler_and_renderer="actual protected Remotion",
        image_generation=False,
        native_agent_inference=False,
        audio="reused hash-pinned Edge Yunxi audio and real WordBoundary times",
        isolation="fixed reviewed fixture host verifier only; deployment not tested",
        human_playback_and_listening=False,
    )
    (out / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
