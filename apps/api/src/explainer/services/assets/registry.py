"""Workspace-scoped receipts survive tenant-scoped pipeline checkpoints."""

import base64
import hashlib
import json
from ...semantic_scene import AssetRequirement
from .raster import raster_receipt, RASTER_VERSION, MAX_IMAGE_BYTES
from . import image_service
from .factory import create_svg, create_preview, requirement_key, FACTORY_VERSION


PRIVATE_FIELDS = {"svg", "image_png", "preview_png"}


def public_receipt(receipt, include_request=False):
    return {
        k: v for k, v in receipt.items() if k not in PRIVATE_FIELDS and (include_request or k != "request")
    }


def _key(req, identity=None):
    if req.provider == "component_svg":
        return requirement_key(req)
    return hashlib.sha256(
        json.dumps(
            [RASTER_VERSION, req.model_dump(), identity or {}], sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


def _data(receipt):
    return (
        receipt["svg"].encode() if "svg" in receipt else base64.b64decode(receipt["image_png"], validate=True)
    )


def _new_receipt(req, settings=None, resolve_image=None, scope="", guard=lambda: None):
    if req.provider != "component_svg":
        ident = image_service.identity(settings) if req.provider == "image_service" else {}
        key = _key(req, ident)
        if req.provider == "image_service":
            data, request_id = image_service.generate(req, settings, key, scope, guard)
        else:
            if resolve_image is None:
                raise ValueError("Project image resolver is not available")
            guard()
            data, request_id = resolve_image(req.project_asset_id), None
        return raster_receipt(req, data, key, ident, request_id)

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
    if req.provider != "component_svg":
        if len(old.get("image_png", "")) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            raise ValueError("Cached raster exceeds budget")
        expected = raster_receipt(
            req,
            _data(old),
            _key(req, old.get("provider_identity")),
            old.get("provider_identity", {}),
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
        ident = image_service.identity(settings) if req.provider == "image_service" else {}
        old = existing.get(req.id)
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
