"""Read-only versioned, repository-owned material catalogue; never a code loader."""

import hashlib
import json
from pathlib import PurePosixPath
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from ..config import ROOT


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_.-]{1,80}$")
    version: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["design", "visual", "motion", "bookend", "font"]
    purpose: str = Field(min_length=5, max_length=500)
    source: str = Field(max_length=240)
    symbol: str = Field(max_length=100)
    provenance: str = Field(max_length=500)
    rights: str = Field(max_length=300)
    readiness: Literal["implemented", "unverified", "blocked"]
    verification: str = Field(max_length=500)


def material_source(relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or str(path) != relative:
        raise ValueError("Material path must be canonical and relative")
    approved = ("packages/engineering-template/src/", "assets/fonts/")
    resolved = (ROOT / relative).resolve()
    if not relative.startswith(approved) or not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("Material source is outside the approved library roots")
    return resolved


def material_library():
    raw = (ROOT / "assets/library/catalog.json").read_bytes()
    value = json.loads(raw)
    materials = [Material.model_validate(item) for item in value["items"]]
    if len({item.id for item in materials}) != len(materials):
        raise ValueError("Material IDs must be unique")
    revision, entries = hashlib.sha256(raw), []
    for item in materials:
        digest = hashlib.sha256(material_source(item.source).read_bytes()).hexdigest()
        revision.update((item.id + digest).encode())
        entries.append({**item.model_dump(), "source_sha256": digest})
    return {
        "schema_version": "1.0",
        "revision": revision.hexdigest(),
        "policy": value["policy"],
        "items": entries,
    }


def validate_material_references(plan, library):
    allowed = {f"library:{item['id']}@{item['version']}": item for item in library["items"]}
    for shot in plan.shots:
        for asset in shot.assets:
            if asset.startswith("library:"):
                if asset not in allowed or allowed[asset]["readiness"] == "blocked":
                    raise ValueError("Unknown or blocked material reference: " + asset)
