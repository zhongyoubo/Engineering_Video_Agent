"""One versioned source/props/assets manifest for preview, review and final rendering."""

import hashlib
import json
from ..config import ROOT


def build_render_plan(props, public, project=None):
    digest = hashlib.sha256()
    template = ROOT / "packages/engineering-template"
    for file in sorted(
        [*[p for p in template.joinpath("src").rglob("*") if p.is_file()], *template.glob("*.mjs")]
    ):
        if file == template / "src/Video.tsx":
            continue
        digest.update(str(file.relative_to(template)).encode())
        digest.update(file.read_bytes())
    vendor = (project or public.parent) / "src/vendor"
    if vendor.is_symlink():
        raise ValueError("Material dependencies cannot be symlinks")
    for file in sorted(vendor.rglob("*")) if vendor.exists() else []:
        if file.is_symlink():
            raise ValueError("Material dependencies cannot be symlinks")
        if file.is_file():
            digest.update(str(file.relative_to(vendor)).encode())
            digest.update(file.read_bytes())
    assets = {
        str(f.relative_to(public)): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(public.rglob("*"))
        if f.is_file()
    }
    presentation = {k: v for k, v in props.items() if k not in {"scenes", "render_plan", "total_frames"}}
    scenes = []
    for scene in props["scenes"]:
        local = {**scene, "start_frame": 0}
        key = hashlib.sha256(
            json.dumps(
                [local, assets, presentation, digest.hexdigest()],
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        semantics = scene.get("semantic_scene") or {}
        scenes.append(
            dict(
                scene_id=scene["id"],
                start_frame=scene["start_frame"],
                frames=scene["frames"],
                dependency_key=key,
                surfaces=[
                    dict(entity=e["id"], target=e["bind_to"], surface="screen")
                    for e in semantics.get("entities", [])
                    if e.get("bind_to")
                ],
                expectations=[scene["id"] + ":" + e["id"] for e in semantics.get("expectations", [])],
                creation=scene.get("creation"),
            )
        )
    return dict(
        schema_version="1.0",
        backend="trusted-remotion",
        renderer_sha256=digest.hexdigest(),
        assets=assets,
        scenes=scenes,
        review="causal before/during/after samples; no full playback/listening claim",
        cache="dependency keys only; rendered scene cache not implemented",
    )


def refresh_plan(project):
    path = project / "props.json"
    props = json.loads(path.read_text(encoding="utf-8"))
    props["render_plan"] = build_render_plan(props, project / "public")
    path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
