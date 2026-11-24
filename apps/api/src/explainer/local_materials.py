"""Operator-managed PNG library outside the repository."""

import hashlib
import json
import re
import stat
from functools import lru_cache
from pathlib import Path, PureWindowsPath
from typing import TypedDict

from .services.assets.raster import MAX_IMAGE_BYTES

MATERIAL_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
TENANT_ID = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")
SHA256 = r"^[a-f0-9]{64}$"
MAX_ITEMS = 256
MAX_INDEX_BYTES = 128 * 1024


class LocalMaterial(TypedDict):
    id: str
    title: str
    origin: str
    rights: str
    sha256: str


def validate_tenant(tenant: str) -> None:
    if not TENANT_ID.fullmatch(tenant) or PureWindowsPath(tenant).is_reserved():
        raise ValueError("Invalid local material tenant ID")


def is_indirection(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def tenant_directory(root: Path, tenant: str) -> Path:
    validate_tenant(tenant)
    directory = root / tenant
    if not root.is_absolute() or is_indirection(root) or is_indirection(directory):
        raise ValueError("Invalid local material library directory")
    if directory.exists() and (not directory.is_dir() or directory.resolve().name != tenant):
        raise ValueError("Local material directory must match the tenant ID")
    return directory


def read_bounded(path: Path, limit: int) -> bytes:
    if is_indirection(path) or not path.is_file():
        raise ValueError("Local material file missing or unsafe")
    with path.open("rb") as source:
        result = source.read(limit + 1)
    if len(result) > limit:
        raise ValueError("Local material file exceeds byte budget")
    return result


@lru_cache(maxsize=32)
def _read_index(index: Path, signature: tuple[int, ...]) -> dict[str, LocalMaterial]:
    # The stat signature makes atomic index replacements visible to the cache.
    value = json.loads(read_bounded(index, MAX_INDEX_BYTES).decode("utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("items"), list):
        raise ValueError("Invalid local material index")
    if len(value["items"]) > MAX_ITEMS:
        raise ValueError("Local material catalog exceeds its item budget")
    items = {}
    for item in value["items"]:
        if not isinstance(item, dict) or set(item) != {"id", "title", "origin", "rights", "sha256", "file"}:
            raise ValueError("Invalid local material entry")
        material_id = item["id"]
        if not isinstance(material_id, str) or not MATERIAL_ID.fullmatch(material_id) or material_id in items:
            raise ValueError("Invalid or duplicate local material ID")
        for field in ("title", "origin", "rights"):
            text = item[field]
            if not isinstance(text, str) or not text.strip() or len(text) > 300:
                raise ValueError("Invalid local material provenance")
            text.encode("utf-8")  # Reject unpaired surrogates escaped in otherwise valid JSON.
        digest = item["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(SHA256, digest) or item["file"] != f"files/{digest}.png":
            raise ValueError("Invalid local material file or hash")
        items[material_id] = LocalMaterial(
            id=material_id, title=item["title"], origin=item["origin"], rights=item["rights"], sha256=digest
        )
    return items


def _index(directory: Path) -> dict[str, LocalMaterial]:
    index = directory / "index.json"
    if is_indirection(index):
        raise ValueError("Local material index must be a regular file")
    try:
        stat = index.stat()
    except FileNotFoundError:
        return {}
    signature = (stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
    return _read_index(index, signature)


def catalog(root: Path | None, tenant: str) -> list[LocalMaterial]:
    if root is None:
        return []
    return [item.copy() for item in _index(tenant_directory(root, tenant)).values()]


def image_bytes(
    root: Path | None, tenant: str, material_id: str, source_sha256: str | None = None
) -> tuple[LocalMaterial, bytes]:
    if root is None or not MATERIAL_ID.fullmatch(material_id):
        raise ValueError("Unknown local material")
    directory = tenant_directory(root, tenant)
    item = _index(directory).get(material_id)
    if item is None or (source_sha256 is not None and item["sha256"] != source_sha256):
        raise ValueError("Unknown local material version")
    files = directory / "files"
    if is_indirection(files):
        raise ValueError("Local material file directory cannot be redirected")
    data = read_bounded(files / f"{item['sha256']}.png", MAX_IMAGE_BYTES)
    if hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError("Local material content changed")
    return item.copy(), data
