"""Typed, curated local packs. No downloaded manifests, source imports or code execution."""

import hashlib
import json
from pathlib import PurePosixPath
from typing import Literal
from pydantic import Field, model_validator
from .config import ROOT
from .specs import Spec

PACK_ROOT = ROOT / "assets/library/packs"


def relative_file(value):
    p = PurePosixPath(value)
    if (
        p.is_absolute()
        or str(p) != value
        or not p.parts
        or "\\" in value
        or ":" in value
        or any(part in {"..", "node_modules"} or part.startswith(".") for part in p.parts)
    ):
        raise ValueError("Pack files must use canonical relative paths")
    return value


class PackFile(Spec):
    path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    role: Literal["code", "image", "model", "preview", "license", "provenance"]

    @model_validator(mode="after")
    def path_role(self):
        relative_file(self.path)
        suffix = PurePosixPath(self.path).suffix.lower()
        allowed = {
            "code": {".tsx", ".ts", ".css"},
            "image": {".png"},
            "model": {".glb"},
            "preview": {".png"},
            "license": {".txt", ".md"},
            "provenance": {".svg", ".tsx", ".ts", ".md", ".json", ".txt"},
        }
        if suffix not in allowed[self.role]:
            raise ValueError("Pack file type differs from its role")
        return self


class PackItem(Spec):
    id: str = Field(pattern=r"^[a-z0-9_.-]{1,80}$")
    name: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=5, max_length=500)
    asset_type: Literal["component", "image", "model"]
    entry: str = Field(min_length=1, max_length=240)
    symbol: str = Field(default="", max_length=100)
    preview: str | None = None
    styles: list[str] = Field(min_length=1, max_length=8)
    subjects: list[str] = Field(min_length=1, max_length=16)
    affordances: list[str] = Field(default_factory=list, max_length=16)
    parameters: dict[str, str] = Field(default_factory=dict, max_length=16)
    dependencies: list[str] = Field(default_factory=list, max_length=32)


class MaterialPack(Spec):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,60}$")
    version: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,20}$")
    origin: str = Field(min_length=5, max_length=500)
    revision: str = Field(min_length=7, max_length=80)
    license: str = Field(min_length=2, max_length=100)
    license_file: str
    files: list[PackFile] = Field(min_length=1, max_length=128)
    items: list[PackItem] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def declared(self):
        files = {f.path: f for f in self.files}
        if len(files) != len(self.files) or len({m.id for m in self.items}) != len(self.items):
            raise ValueError("Pack files and material IDs must be unique")
        if self.license_file not in files or files[self.license_file].role != "license":
            raise ValueError("Pack requires its retained license")
        for item in self.items:
            if not item.id.startswith(f"pack.{self.id}."):
                raise ValueError("Material ID must belong to its pack namespace")
            roles = {"component": "code", "image": "image", "model": "model"}
            if item.entry not in files or files[item.entry].role != roles[item.asset_type]:
                raise ValueError("Material entry has a missing or wrong file role")
            if item.asset_type == "component" and not item.symbol:
                raise ValueError("Component requires its exported symbol")
            if item.preview and (item.preview not in files or files[item.preview].role != "preview"):
                raise ValueError("Material preview is not a declared PNG")
            if item.asset_type != "component" and not item.preview:
                raise ValueError("Binary materials require a preview")
            if any(p not in files or files[p].role != "code" for p in item.dependencies):
                raise ValueError("Component dependencies must be declared code files")
        return self


def pack_file(directory, entry):
    relative_file(entry.path)
    path = directory / entry.path
    if any(p.is_symlink() for p in [directory, path, *path.parents] if p.is_relative_to(PACK_ROOT)):
        raise ValueError("Pack symlinks are forbidden")
    if not path.is_file() or path.stat().st_size > 12 * 1024 * 1024:
        raise ValueError("Missing or oversized pack file")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry.sha256:
        raise ValueError("Curated pack file hash differs from its manifest")
    return path


def load_packs():
    index = PACK_ROOT / "index.json"
    if not index.exists():
        return []
    if PACK_ROOT.is_symlink() or index.is_symlink() or index.stat().st_size > 32768:
        raise ValueError("Invalid curated pack index")
    paths = json.loads(index.read_text())
    if not isinstance(paths, list) or len(paths) > 32 or len(set(paths)) != len(paths):
        raise ValueError("Invalid curated pack index")
    packs, ids = [], set()
    for name in paths:
        relative_file(name)
        path = PACK_ROOT / name
        if (
            any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(PACK_ROOT))
            or path.name != "manifest.json"
            or path.stat().st_size > 128 * 1024
        ):
            raise ValueError("Invalid pack manifest")
        pack = MaterialPack.model_validate_json(path.read_text())
        if (pack.id, pack.version) in ids:
            raise ValueError("Duplicate pack version")
        ids.add((pack.id, pack.version))
        files = {f.path: pack_file(path.parent, f) for f in pack.files}
        if sum(p.stat().st_size for p in files.values()) > 64 * 1024 * 1024:
            raise ValueError("Pack exceeds byte budget")
        stamp = hashlib.sha256(path.read_bytes()).hexdigest()
        packs.append((pack, path.parent, files, stamp))
    return packs


def resolve_material(ref):
    for pack, directory, files, stamp in load_packs():
        for item in pack.items:
            if ref == f"library:{item.id}@{pack.version}":
                return pack, item, files, stamp
    raise ValueError("Unknown versioned curated material reference")


def material_pack_entries():
    entries = []
    for pack, directory, files, stamp in load_packs():
        for item in pack.items:
            entries.append(
                dict(
                    id=item.id,
                    version=pack.version,
                    name=item.name,
                    kind="visual",
                    purpose=item.purpose,
                    source=str(files[item.entry].relative_to(ROOT)),
                    symbol=item.symbol,
                    provenance=f"{pack.origin}@{pack.revision}",
                    rights=pack.license,
                    readiness="implemented",
                    verification="Curated hash-pinned files; actual pack verification is recorded separately; no native-quality certification",
                    source_sha256=hashlib.sha256(files[item.entry].read_bytes()).hexdigest(),
                    pack_id=pack.id,
                    pack_sha256=stamp,
                    asset_type=item.asset_type,
                    styles=item.styles,
                    subjects=item.subjects,
                    affordances=item.affordances,
                    parameters=item.parameters,
                    preview=f"/api/v1/material-library/{item.id}/preview?version={pack.version}"
                    if item.preview
                    else None,
                    module=f"src/vendor/{pack.id}/{item.entry}" if item.asset_type == "component" else None,
                )
            )
    return entries
