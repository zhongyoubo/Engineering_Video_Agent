"""Workspace-scoped receipts survive tenant-scoped pipeline checkpoints."""

import base64
import hashlib
import json
from pathlib import PurePosixPath
from ...semantic_scene import AssetRequirement
from .factory import create_svg, create_preview, requirement_key, FACTORY_VERSION


def request_assets(workspace, requirements, guard):
    guard()
    existing = workspace.state.setdefault("generated_assets", {})
    if len(existing) + len({r.id for r in requirements} - existing.keys()) > 24:
        raise ValueError("Generated asset count exceeds project budget")
    staged = []
    for request in requirements:
        req = AssetRequirement.model_validate(request)
        key = requirement_key(req)
        old = existing.get(req.id)
        if old and old["request_hash"] == key:
            data = old["svg"].encode()
            receipt = old
        else:
            data, metadata = create_svg(req)
            digest = hashlib.sha256(data).hexdigest()
            receipt = dict(
                request_hash=key,
                sha256=digest,
                filename=f"generated/{digest}.svg",
                svg=data.decode(),
                request=req.model_dump(),
                factory_version=FACTORY_VERSION,
                **metadata,
            )
        preview = create_preview(req)
        receipt = {
            **receipt,
            "preview_filename": f"generated/{receipt['sha256']}.preview.png",
            "preview_sha256": hashlib.sha256(preview).hexdigest(),
            "preview_png": base64.b64encode(preview).decode(),
        }
        staged.append((req.id, receipt, data))
    if (
        sum(
            len(r["svg"].encode()) + len(base64.b64decode(r["preview_png"]))
            for r in {**existing, **{id: r for id, r, _ in staged}}.values()
        )
        > 8 * 1024 * 1024
    ):
        raise ValueError("Generated asset bytes exceed project budget")
    guard()  # Cancellation/lease guard must pass before publication.
    for id, receipt, data in staged:
        path = workspace.project / "public" / receipt["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.with_suffix(".preview.png").write_bytes(base64.b64decode(receipt["preview_png"]))
        existing[id] = receipt
    keep = {r[k] for r in existing.values() for k in ["filename", "preview_filename"]}
    for f in (workspace.project / "public/generated").glob("*"):
        if "generated/" + f.name not in keep and f.is_file():
            f.unlink()
    props_path = workspace.project / "props.json"
    props = json.loads(props_path.read_text())
    props["generated_assets"] = {id: v["filename"] for id, v in existing.items()}
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2))
    from ..render_plan import refresh_plan

    refresh_plan(workspace.project)
    workspace.invalidate()
    return [
        dict(id=id, **{k: v for k, v in rec.items() if k not in {"svg", "request", "preview_png"}})
        for id, rec, _ in staged
    ]


def restore_assets(workspace):
    # Revalidate recovered data and regenerate from the controlled input; never trust recovered SVG text/path.
    for id, receipt in workspace.state.get("generated_assets", {}).items():
        req = AssetRequirement.model_validate(receipt["request"])
        if id != req.id or receipt["request_hash"] != requirement_key(req):
            raise ValueError("Generated asset receipt version changed; request the asset again")
        data, _ = create_svg(req)
        digest = hashlib.sha256(data).hexdigest()
        expected = f"generated/{digest}.svg"
        if (
            receipt["filename"] != expected
            or receipt["sha256"] != digest
            or str(PurePosixPath(expected)) != expected
        ):
            raise ValueError("Recovered asset receipt is inconsistent")
        path = workspace.project / "public" / expected
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        preview = create_preview(req)
        if (
            receipt.get("preview_filename") != f"generated/{digest}.preview.png"
            or receipt.get("preview_sha256") != hashlib.sha256(preview).hexdigest()
        ):
            raise ValueError("Recovered preview receipt is inconsistent")
        path.with_suffix(".preview.png").write_bytes(preview)
    return {id: v["filename"] for id, v in workspace.state.get("generated_assets", {}).items()}
