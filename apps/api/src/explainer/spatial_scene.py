"""Bounded, data-only spatial and quantity vocabulary. No executable code or external URLs."""

from pydantic import Field, model_validator
from .specs import Spec

SPATIAL_COMPONENTS = {"SpatialCity", "QuantityMatrix", "NodeNetwork"}


class SpatialSpec(Spec):
    seed: int = Field(default=17, ge=0, le=2147483647)
    count: int = Field(default=240, ge=12, le=768)
    columns: int = Field(default=20, ge=4, le=32)
    camera_radius: float = Field(default=34, ge=12, le=90)
    camera_height: float = Field(default=18, ge=5, le=50)
    orbit_degrees: float = Field(default=36, ge=-90, le=90)
    source_node: int = Field(default=0, ge=0, le=63)
    effect_parameter_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    asset_keys: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def assets(self):
        import re

        if len(set(self.asset_keys)) != len(self.asset_keys) or any(
            not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", key) for key in self.asset_keys
        ):
            raise ValueError("Spatial assets need unique registered keys, never paths or URLs")
        return self


def spatial_asset_keys(entity):
    """Works on a typed entity or persisted JSON; the same resolver owns all consumers."""
    if isinstance(entity, dict):
        spec = entity.get("spatial") or {}
        return spec.get("asset_keys", [])
    return entity.spatial.asset_keys if entity.spatial else []
