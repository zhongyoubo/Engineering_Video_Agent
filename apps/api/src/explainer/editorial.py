"""Data-only creator brief and publication contracts; independent of renderer types."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

PresentationProfile = Literal["creator", "internal_demo", "engineering_report"]
SceneRole = Literal[
    "content",
    "opening",
    "hook",
    "problem",
    "argument",
    "example",
    "mechanism",
    "demonstration",
    "limitation",
    "recommendation",
    "closing",
]


class EditorialModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EditorialBrief(EditorialModel):
    intent: Literal["auto", "viewpoint", "advice", "analysis", "knowledge", "explanation"] = "auto"
    subject_kind: Literal["auto", "project", "knowledge", "concept", "mechanism", "workflow"] = "auto"
    core_message: str = Field(default="", max_length=500)
    viewer_takeaway: str = Field(default="", max_length=500)


class CoverSpec(EditorialModel):
    headline: str = Field(min_length=1, max_length=100)
    subtitle: str = Field(default="", max_length=160)


class SupportPoint(EditorialModel):
    message: str = Field(min_length=1, max_length=500)
    claim_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class EditorialPlan(EditorialModel):
    audience_question: str = Field(min_length=1, max_length=500)
    core_message: str = Field(min_length=1, max_length=500)
    viewer_takeaway: str = Field(min_length=1, max_length=500)
    hook: str = Field(min_length=1, max_length=500)
    supports: list[SupportPoint] = Field(min_length=1, max_length=6)
    closing: str = Field(min_length=1, max_length=500)
    cover: CoverSpec


class ViewerDisclosure(EditorialModel):
    text: str = Field(min_length=1, max_length=100)
    start_seconds: float = Field(default=0, ge=0, le=180)
    end_seconds: float = Field(default=4, gt=0, le=180)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Disclosure end must follow its start")
        return self
