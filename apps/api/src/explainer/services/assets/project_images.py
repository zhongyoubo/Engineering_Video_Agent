"""Immutable, authenticated project image catalog; tenant-only IDs are insufficient."""

import hashlib
import json
from ...db import encode, uid
from .raster import canonical_png
import time


def catalog(db, tenant, project_id):
    return [
        dict(id=r["id"], **json.loads(r["metadata"]))
        for r in db.all(
            "SELECT id,metadata FROM project_images WHERE tenant=? AND project_id=? ORDER BY created,id",
            (tenant, project_id),
        )
    ]


def put_image(db, store, tenant, project_id, data, title):
    blob, _, meta = canonical_png(data)
    meta.update(title=title, sha256=hashlib.sha256(blob).hexdigest(), provenance="user_import")
    # Content-addressed storage precedes the quota lock; a rejected catalog insert may leave
    # an unreferenced object, never a cross-project catalog entry.
    asset = store.put(tenant, blob, "project-image", "image.png", "image/png")
    with db.transaction() as conn:
        db.lock_tenant(conn, tenant)
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM project_images WHERE tenant=? AND project_id=?",
            (tenant, project_id),
        ).fetchone()["n"]
        if count >= 24:
            raise ValueError("Project image catalog exceeds 24 assets")
        id = uid("mat")
        conn.execute(
            "INSERT INTO project_images VALUES(?,?,?,?,?,?)",
            (id, tenant, project_id, asset["id"], encode(meta), time.time()),
        )
    return dict(id=id, **meta)


def resolve_image(db, store, tenant, project_id, id):
    row = db.one(
        "SELECT asset_id,metadata FROM project_images WHERE tenant=? AND project_id=? AND id=?",
        (tenant, project_id, id),
    )
    if not row:
        raise ValueError("Image is not registered in this project")
    _, path = store.get(tenant, row["asset_id"])
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != json.loads(row["metadata"])["sha256"]:
        raise ValueError("Project image checksum mismatch")
    return blob
