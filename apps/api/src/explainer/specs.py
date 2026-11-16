"""Versioned, data-only production settings shared by API and authoring tools."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RenderProfile(Spec):
    resolution: Literal["1080p", "4k"] = "1080p"
    fps: Literal[30] = 30

    @property
    def width(self):
        return 3840 if self.resolution == "4k" else 1920

    @property
    def height(self):
        return self.width * 9 // 16


class VoiceSpec(Spec):
    voice_id: str = Field(default="", max_length=100)
    model: str = Field(default="", max_length=100)
    speed: float = Field(default=1.0, ge=0.85, le=1.15)
    revision: str = Field(default="1", min_length=1, max_length=80)


class CueAnchor(Spec):
    phrase: str = Field(min_length=1, max_length=160)
    occurrence: int = Field(default=1, ge=1, le=30)
    edge: Literal["start", "end"] = "start"
    offset_ms: int = Field(default=0, ge=-2000, le=2000)


class VisualElement(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    label: str = Field(min_length=1, max_length=100)


class MotionEvent(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    target: str
    action: Literal["reveal", "highlight", "progress"]
    anchor: CueAnchor
    duration_ms: int = Field(default=700, ge=100, le=5000)


class SceneSpec(Spec):
    schema_version: Literal["4.0"] = "4.0"
    purpose: str = Field(min_length=5, max_length=500)
    chapter: str = Field(default="", max_length=100)
    pattern: Literal["overview", "code_scan", "compare", "graph", "capacity", "queue", "depth"]
    elements: list[VisualElement] = Field(min_length=1, max_length=8)
    events: list[MotionEvent] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def valid_references(self):
        ids = {e.id for e in self.elements}
        if len(ids) != len(self.elements):
            raise ValueError("Visual element IDs must be unique")
        if len({e.id for e in self.events}) != len(self.events):
            raise ValueError("Motion event IDs must be unique")
        if any(e.target not in ids for e in self.events):
            raise ValueError("Motion target is not a visual element")
        if len({(e.target, e.action) for e in self.events}) != len(self.events):
            raise ValueError("Only one event per target/action is supported")
        return self


class CompiledEvent(Spec):
    id: str
    target: str
    action: Literal["reveal", "highlight", "progress"]
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    timing_source: Literal["measured_words", "estimated_draft"]

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_frame <= self.start_frame:
            raise ValueError("Motion event must have positive duration")
        return self
