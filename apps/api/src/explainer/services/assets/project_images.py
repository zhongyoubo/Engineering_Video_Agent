"""Immutable, authenticated project image catalog; tenant-only IDs are insufficient."""

import hashlib
import json
import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from ...db import encode, uid
from ...local_materials import MATERIAL_ID, SHA256
from .raster import canonical_png


class LocalImageSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    local_material_id: str = Field(pattern=MATERIAL_ID.pattern)
    source_sha256: str = Field(pattern=SHA256)
    origin: str = Field(min_length=1, max_length=300)
    rights: str = Field(min_length=1, max_length=300)


@dataclass(frozen=True)
class ResolvedProjectImage:
    data: bytes
    local_source: LocalImageSource | None


def catalog(db, tenant, project_id):
    return [
        dict(id=r["id"], **json.loads(r["metadata"]))
        for r in db.all(
            "SELECT id,metadata FROM project_images WHERE tenant=? AND project_id=? ORDER BY created,id",
            (tenant, project_id),
        )
    ]


def put_image(db, store, tenant, project_id, data, title, local_source: LocalImageSource | None = None):
    blob, _, meta = canonical_png(data)
    meta.update(title=title, sha256=hashlib.sha256(blob).hexdigest(), provenance="user_import")
    if local_source is not None:
        meta.update(local_source.model_dump(), provenance="local_library")
    # Content-addressed storage precedes the quota lock; a rejected catalog insert may leave
    # an unreferenced object, never a cross-project catalog entry.
    asset = store.put(tenant, blob, "project-image", "image.png", "image/png")
    with db.transaction() as conn:
        db.lock_tenant(conn, tenant)
        rows = conn.execute(
            "SELECT id,metadata FROM project_images WHERE tenant=? AND project_id=? ORDER BY created,id",
            (tenant, project_id),
        ).fetchall()
        if local_source is not None:
            for row in rows:
                existing = json.loads(row["metadata"])
                if (
                    existing.get("local_material_id") == local_source.local_material_id
                    and existing.get("source_sha256") == local_source.source_sha256
                ):
                    return dict(id=row["id"], **existing)
        if len(rows) >= 24:
            raise ValueError("Project image catalog exceeds 24 assets")
        id = uid("mat")
        conn.execute(
            "INSERT INTO project_images VALUES(?,?,?,?,?,?)",
            (id, tenant, project_id, asset["id"], encode(meta), time.time()),
        )
    return dict(id=id, **meta)


def resolve_image(db, store, tenant, project_id, id):
    return resolve_image_with_source(db, store, tenant, project_id, id).data


def resolve_image_with_source(db, store, tenant, project_id, id) -> ResolvedProjectImage:
    row = db.one(
        "SELECT asset_id,metadata FROM project_images WHERE tenant=? AND project_id=? AND id=?",
        (tenant, project_id, id),
    )
    if not row:
        raise ValueError("Image is not registered in this project")
    _, path = store.get(tenant, row["asset_id"])
    blob = path.read_bytes()
    metadata = json.loads(row["metadata"])
    if hashlib.sha256(blob).hexdigest() != metadata["sha256"]:
        raise ValueError("Project image checksum mismatch")
    source = None
    if metadata.get("provenance") == "local_library":
        source = LocalImageSource.model_validate({name: metadata.get(name) for name in LocalImageSource.model_fields})
    return ResolvedProjectImage(blob, source)
