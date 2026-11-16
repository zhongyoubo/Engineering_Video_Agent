import hashlib
import hmac

from fastapi import Depends, HTTPException, Request

from .config import get_settings


def identify(token, settings):
    candidate = hashlib.sha256(token.encode()).digest()
    for tenant, expected in settings.keys().items():
        if hmac.compare_digest(candidate, hashlib.sha256(expected.encode()).digest()):
            return tenant
    return None


def tenant(request: Request, settings=Depends(get_settings)):
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("explainer_session", "")
    found = identify(token, settings)
    if not found:
        raise HTTPException(401, "请使用启动时生成的访问密钥登录")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins.split(","):
            raise HTTPException(403, "Origin rejected")
    return found


def owned(db, table, identifier, tenant_id):
    if table not in {"projects", "inputs", "revisions", "jobs", "assets"}:
        raise ValueError("Unknown resource")
    row = db.one(f"SELECT * FROM {table} WHERE id=? AND tenant=?", (identifier, tenant_id))
    if not row:
        raise HTTPException(404, "Resource not found")
    return row
