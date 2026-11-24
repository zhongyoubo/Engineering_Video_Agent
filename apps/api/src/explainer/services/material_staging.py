"""Selectively copy reviewed local code packs; no import/evaluation of their source."""

import hashlib
import json
from ..material_packs import material_resolver, relative_file


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
    resolve = material_resolver() if refs else None
    for ref in sorted(refs):
        guard()
        pack, item, files, stamp = resolve(ref)
        if pack.id in versions and versions[pack.id] != pack.version:
            raise ValueError("Select one version per pack in a workspace")
        versions[pack.id] = pack.version
        if item.asset_type == "component":
            for name in sorted({item.entry, *item.dependencies}):
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
    existing = []
    for name in ["src/vendor", "public/library"]:
        root = checked_path(workspace, name)
        for path in root.rglob("*") if root.exists() else []:
            checked_path(workspace, path.relative_to(workspace.project).as_posix())
            if path.is_file():
                existing.append(path)
    before = workspace.fingerprint()
    try:
        for name, data in staged.items():
            path = workspace.project / name
            if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(workspace.project)):
                raise ValueError("Staged library paths cannot be symlinks")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for path in existing:
            if path.relative_to(workspace.project).as_posix() not in staged:
                path.unlink()
        workspace.state["material_selection"] = manifest
        props_path = workspace.project / "props.json"
        if props_path.is_file():
            props = json.loads(props_path.read_text(encoding="utf-8"))
            props["material_packs"] = manifest
            props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
            from .render_plan import refresh_plan

            refresh_plan(workspace.project)
        return manifest
    finally:
        if workspace.fingerprint() != before:
            workspace.invalidate()


def checked_path(workspace, name):
    relative_file(name)
    if not (
        name in {"src/vendor", "public/library"}
        or name.startswith("src/vendor/")
        or name.startswith("public/library/")
    ):
        raise ValueError("Invalid material dependency path")
    path = workspace.project / name
    if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(workspace.project)):
        raise ValueError("Material dependencies cannot be symlinks")
    return path


def validated_selection(manifest):
    if manifest is None:
        manifest = dict(references=[], materials={}, files={})
    # Rebuild from reviewed pack refs, never trust a recovered digest/file list.
    staged, expected = selection_files(manifest.get("references", []))
    if manifest != expected:
        raise ValueError("Selected material manifest differs from reviewed packs")
    return staged, expected


def verify_staged_materials(workspace):
    staged, manifest = validated_selection(workspace.state.get("material_selection"))
    props_path = workspace.project / "props.json"
    if props_path.is_file():
        props = json.loads(props_path.read_text(encoding="utf-8"))
        if props.get("material_packs", manifest) != manifest:
            raise ValueError("Props material selection differs from workspace")
    for name, data in staged.items():
        path = checked_path(workspace, name)
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError("Selected material bytes differ from their staged manifest")
    for name in ["src/vendor", "public/library"]:
        root = checked_path(workspace, name)
        for path in root.rglob("*") if root.exists() else []:
            if path.is_symlink() or (
                path.is_file() and path.relative_to(workspace.project).as_posix() not in staged
            ):
                raise ValueError("Undeclared material dependency")
    return manifest
