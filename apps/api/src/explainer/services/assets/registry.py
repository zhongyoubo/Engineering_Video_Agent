"""Workspace-scoped receipts survive tenant-scoped pipeline checkpoints."""

import base64
import hashlib
import json
from ...semantic_scene import AssetRequirement
from .factory import create_svg, create_preview, requirement_key, FACTORY_VERSION


def _new_receipt(req):
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
        sum(
            len(r["svg"].encode()) + len(base64.b64decode(r["preview_png"], validate=True))
            for r in receipts.values()
        )
        > 8 * 1024 * 1024
    ):
        raise ValueError("Generated asset bytes exceed project budget")


def _write_assets(workspace, receipts):
    for r in receipts.values():
        path = workspace.project / "public" / r["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r["svg"].encode())
        path.with_suffix(".preview.png").write_bytes(base64.b64decode(r["preview_png"], validate=True))
    keep = {r[k] for r in receipts.values() for k in ["filename", "preview_filename"]}
    for f in (workspace.project / "public/generated").glob("*"):
        if "generated/" + f.name not in keep and f.is_file():
            f.unlink()


def _cached_receipt(req, old):
    """Only reuse canonical in-memory receipts; recovery rebuilds them from typed input."""
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


def request_assets(workspace, requirements, guard):
    guard()
    existing = workspace.state.setdefault("generated_assets", {})
    requests = [AssetRequirement.model_validate(r) for r in requirements]
    if len(existing) + len({r.id for r in requests} - existing.keys()) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    staged = {}
    for req in requests:
        old = existing.get(req.id)
        staged[req.id] = (
            _cached_receipt(req, old)
            if old and old["request_hash"] == requirement_key(req)
            else _new_receipt(req)
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
    return [
        dict(id=id, **{k: v for k, v in rec.items() if k not in {"svg", "request", "preview_png"}})
        for id, rec in staged.items()
    ]


def restore_assets(workspace):
    """Validate the whole checkpoint, then publish canonical bytes AND cache receipts."""
    existing = workspace.state.get("generated_assets", {})
    if len(existing) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    staged = {}
    for id, receipt in existing.items():
        req = AssetRequirement.model_validate(receipt["request"])
        if id != req.id or receipt["request_hash"] != requirement_key(req):
            raise ValueError("Generated asset receipt version changed; request the asset again")
        canonical = _new_receipt(req)
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
