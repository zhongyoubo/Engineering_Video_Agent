"""Workspace-scoped receipts survive tenant-scoped pipeline checkpoints."""

import base64
import hashlib
import json
from ...semantic_scene import AssetRequirement
from .raster import raster_receipt, RASTER_VERSION, MAX_IMAGE_BYTES
from . import image_service
from .factory import create_svg, create_preview, requirement_key, FACTORY_VERSION
from .project_images import LocalImageSource, ResolvedProjectImage


PRIVATE_FIELDS = {"svg", "image_png", "preview_png", "file_data", "license_text"}


def public_receipt(receipt, include_request=False):
    return {
        k: v for k, v in receipt.items() if k not in PRIVATE_FIELDS and (include_request or k != "request")
    }


def _key(req, identity=None):
    if req.provider == "library_asset":
        from .library import library_key

        return library_key(req)
    if req.provider == "component_svg":
        return requirement_key(req)
    return hashlib.sha256(
        json.dumps(
            [RASTER_VERSION, req.model_dump(), identity or {}], sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


def _data(receipt):
    if "file_data" in receipt:
        if len(receipt["file_data"]) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            raise ValueError("Cached library file exceeds budget")
        return base64.b64decode(receipt["file_data"], validate=True)
    return (
        receipt["svg"].encode() if "svg" in receipt else base64.b64decode(receipt["image_png"], validate=True)
    )


def _new_receipt(req, settings=None, resolve_image=None, scope="", guard=lambda: None):
    if req.provider == "library_asset":
        from .library import library_receipt

        guard()
        return library_receipt(req)
    if req.provider != "component_svg":
        ident = image_service.identity(settings) if req.provider == "image_service" else {}
        if req.provider == "image_service":
            data, request_id = image_service.generate(req, settings, _key(req, ident), scope, guard)
        else:
            if resolve_image is None:
                raise ValueError("Project image resolver is not available")
            guard()
            resolved = resolve_image(req.project_asset_id)
            if isinstance(resolved, ResolvedProjectImage):
                data = resolved.data
                if resolved.local_source is not None:
                    ident = {"local_material": resolved.local_source.model_dump()}
            else:
                data = resolved
            request_id = None
        return raster_receipt(req, data, _key(req, ident), ident, request_id)

    data, metadata = create_svg(req)
    digest = hashlib.sha256(data).hexdigest()
    preview = create_preview(req)
    return dict(
        request_hash=requirement_key(req),
        sha256=digest,
        filename=f"generated/{digest}.svg",
        svg=data.decode(),
        request=req.model_dump(),
        factory_version=FACTORY_VERSION,
        **metadata,
        preview_filename=f"generated/{digest}.preview.png",
        preview_sha256=hashlib.sha256(preview).hexdigest(),
        preview_png=base64.b64encode(preview).decode(),
    )


def _check_budget(receipts):
    if len(receipts) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    if (
        sum(len(_data(r)) + len(base64.b64decode(r["preview_png"], validate=True)) for r in receipts.values())
        > 64 * 1024 * 1024
    ):
        raise ValueError("Generated asset bytes exceed project budget")


def _write_assets(workspace, receipts):
    for r in receipts.values():
        path = workspace.project / "public" / r["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_data(r))
        path.with_suffix(".preview.png").write_bytes(base64.b64decode(r["preview_png"], validate=True))
    keep = {r[k] for r in receipts.values() for k in ["filename", "preview_filename"]}
    for f in (workspace.project / "public/generated").glob("*"):
        if "generated/" + f.name not in keep and f.is_file():
            f.unlink()


def _cached_receipt(req, old):
    """Validate retained raster bytes without another inference or untrusted path writes."""
    if req.provider == "library_asset":
        from .library import library_receipt

        expected = library_receipt(req)
        if old != expected:
            raise ValueError("Cached library material receipt is inconsistent")
        return expected
    if req.provider != "component_svg":
        if len(old.get("image_png", "")) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            raise ValueError("Cached raster exceeds budget")
        identity = old.get("provider_identity", {})
        if req.provider == "project_image" and identity:
            if not isinstance(identity, dict) or set(identity) != {"local_material"}:
                raise ValueError("Invalid local project image identity")
            LocalImageSource.model_validate(identity["local_material"])
        expected = raster_receipt(
            req,
            _data(old),
            _key(req, identity),
            identity,
            old.get("provider_request_id"),
        )
        if old != expected:
            raise ValueError("Cached raster asset receipt is inconsistent")
        return expected
    data = old["svg"].encode()
    preview = base64.b64decode(old["preview_png"], validate=True)
    digest = hashlib.sha256(data).hexdigest()
    if (
        old["sha256"] != digest
        or old["filename"] != f"generated/{digest}.svg"
        or old["preview_filename"] != f"generated/{digest}.preview.png"
        or old["preview_sha256"] != hashlib.sha256(preview).hexdigest()
        or old["request"] != req.model_dump()
        or old["factory_version"] != FACTORY_VERSION
    ):
        raise ValueError("Cached generated asset receipt is inconsistent")
    return {**old}


def request_assets(workspace, requirements, guard, settings=None, resolve_image=None, scope=""):
    guard()
    existing = workspace.state.setdefault("generated_assets", {})
    requests = [AssetRequirement.model_validate(r) for r in requirements]
    if len(existing) + len({r.id for r in requests} - existing.keys()) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    if len({r.id for r in requests}) != len(requests):
        raise ValueError("Duplicate asset request IDs")
    staged = {}
    for req in requests:
        guard()
        old = existing.get(req.id)
        if req.provider == "image_service":
            ident = image_service.identity(settings)
        elif req.provider == "project_image" and old:
            ident = old.get("provider_identity", {})
        else:
            ident = {}
        staged[req.id] = (
            _cached_receipt(req, old)
            if old and old["request_hash"] == _key(req, ident)
            else _new_receipt(req, settings, resolve_image, scope or str(workspace.root), guard)
        )
    candidate = {**existing, **staged}
    _check_budget(candidate)
    guard()  # Cancellation/lease guard must pass before publication.
    prior = workspace.fingerprint()
    try:
        _write_assets(workspace, candidate)
        existing.update(staged)
        props_path = workspace.project / "props.json"
        props = json.loads(props_path.read_text())
        props["generated_assets"] = {id: v["filename"] for id, v in existing.items()}
        props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2))
        from ..render_plan import refresh_plan

        refresh_plan(workspace.project)
    finally:
        # A repaired file or partial I/O change also invalidates previous evidence.
        if workspace.fingerprint() != prior:
            workspace.invalidate()
    return [dict(id=id, **public_receipt(rec)) for id, rec in staged.items()]


def restore_assets(workspace):
    """Validate the whole checkpoint, then publish canonical bytes AND cache receipts."""
    existing = workspace.state.get("generated_assets", {})
    if len(existing) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    staged = {}
    for id, receipt in existing.items():
        req = AssetRequirement.model_validate(receipt["request"])
        if id != req.id or receipt["request_hash"] != _key(req, receipt.get("provider_identity")):
            raise ValueError("Generated asset receipt version changed; request the asset again")
        canonical = _new_receipt(req) if req.provider == "component_svg" else _cached_receipt(req, receipt)
        if any(
            receipt.get(k) != canonical[k]
            for k in ["filename", "sha256", "preview_filename", "preview_sha256", "factory_version"]
        ):
            raise ValueError("Recovered asset receipt is inconsistent")
        staged[id] = canonical
    _check_budget(staged)
    _write_assets(workspace, staged)
    for id, receipt in staged.items():
        existing[id].clear()
        existing[id].update(receipt)
    return {id: v["filename"] for id, v in existing.items()}
