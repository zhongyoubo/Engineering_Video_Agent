"""Selectively copy reviewed local code packs; no import/evaluation of their source."""

import hashlib
import json
from ..material_packs import resolve_material, relative_file


def plan_material_refs(plan, props):
    refs = {
        ref for shot in plan.get("shots", []) for ref in shot.get("assets", []) if ref.startswith("library:")
    }
    refs.update(
        req["library_ref"]
        for shot in plan.get("shots", [])
        for req in shot.get("asset_requirements", [])
        if req.get("library_ref")
    )
    refs.update(
        e["library_ref"]
        for s in props.get("scenes", [])
        for e in (s.get("creation") or {}).get("elements", [])
        if e.get("library_ref")
    )
    # Existing legacy catalog entries do not need a copied pack.
    return sorted(ref for ref in refs if ref.startswith("library:pack."))


def selection_files(refs, guard=lambda: None):
    if len(refs) > 64 or len(set(refs)) != len(refs):
        raise ValueError("Material selection exceeds its bounded unique reference list")
    staged, records, versions = {}, {}, {}
    for ref in sorted(refs):
        guard()
        pack, item, files, stamp = resolve_material(ref)
        if pack.id in versions and versions[pack.id] != pack.version:
            raise ValueError("Select one version per pack in a workspace")
        versions[pack.id] = pack.version
        if item.asset_type == "component":
            for name in {item.entry, *item.dependencies}:
                staged[f"src/vendor/{pack.id}/{name}"] = files[name].read_bytes()
        staged[f"public/library/{pack.id}/LICENSE.txt"] = files[pack.license_file].read_bytes()
        if item.preview:
            staged[f"public/library/{pack.id}/{item.preview}"] = files[item.preview].read_bytes()
        records[ref] = dict(
            pack=pack.id,
            version=pack.version,
            bundle_sha256=stamp,
            asset_type=item.asset_type,
            symbol=item.symbol,
            module=f"src/vendor/{pack.id}/{item.entry}" if item.asset_type == "component" else None,
            preview=f"library/{pack.id}/{item.preview}" if item.preview else None,
            origin=pack.origin,
            revision=pack.revision,
            license=pack.license,
        )
    manifest = dict(
        references=sorted(refs),
        materials=records,
        files={p: hashlib.sha256(b).hexdigest() for p, b in staged.items()},
    )
    return staged, manifest


def stage_materials(workspace, refs, guard=lambda: None):
    staged, manifest = selection_files(refs, guard)
    guard()
    # Validate every destination before writing; no partial writes for an invalid path.
    for name in staged:
        checked_path(workspace, name)
    before = workspace.fingerprint()
    try:
        for name, data in staged.items():
            path = workspace.project / name
            if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(workspace.project)):
                raise ValueError("Staged library paths cannot be symlinks")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for root in [workspace.project / "src/vendor", workspace.project / "public/library"]:
            if root.is_symlink():
                raise ValueError("Staged library directory cannot be a symlink")
            for path in root.rglob("*") if root.exists() else []:
                if path.is_symlink():
                    raise ValueError("Staged library symlinks are forbidden")
                if path.is_file() and str(path.relative_to(workspace.project)) not in staged:
                    path.unlink()
        workspace.state["material_selection"] = manifest
        props_path = workspace.project / "props.json"
        if props_path.is_file():
            props = json.loads(props_path.read_text())
            props["material_packs"] = manifest
            props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2))
            from .render_plan import refresh_plan

            refresh_plan(workspace.project)
        return manifest
    finally:
        if workspace.fingerprint() != before:
            workspace.invalidate()


def checked_path(workspace, name):
    relative_file(name)
    if not (name.startswith("src/vendor/") or name.startswith("public/library/")):
        raise ValueError("Invalid material dependency path")
    path = workspace.project / name
    if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(workspace.project)):
        raise ValueError("Material dependencies cannot be symlinks")
    return path


def verify_staged_materials(workspace):
    manifest = workspace.state.get("material_selection")
    if manifest is None:
        manifest = dict(references=[], materials={}, files={})
    # Rebuild from reviewed pack refs, never trust a recovered digest/file list.
    staged, expected = selection_files(manifest.get("references", []))
    if manifest != expected:
        raise ValueError("Selected material manifest differs from reviewed packs")
    props_path = workspace.project / "props.json"
    if props_path.is_file():
        props = json.loads(props_path.read_text())
        if props.get("material_packs", expected) != expected:
            raise ValueError("Props material selection differs from workspace")
    for name, data in staged.items():
        path = checked_path(workspace, name)
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError("Selected material bytes differ from their staged manifest")
    for name in ["src/vendor", "public/library"]:
        root = workspace.project / name
        if root.is_symlink():
            raise ValueError("Material dependencies cannot be symlinks")
        for path in root.rglob("*") if root.exists() else []:
            if path.is_symlink() or (
                path.is_file() and str(path.relative_to(workspace.project)) not in staged
            ):
                raise ValueError("Undeclared material dependency")
    return manifest
