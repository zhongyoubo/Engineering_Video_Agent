"""Data-only creator brief and publication contracts; independent of renderer types."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .content_taxonomy import (
    ContentIntent,
    RequestedIntent,
    ContentSubject,
    RequestedSubject,
    PresentationForm,
    AudienceLevel,
    BeatFunction,
)

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
    intent: RequestedIntent = "auto"
    secondary_intents: list[ContentIntent] = Field(default_factory=list, max_length=2)
    subject_kind: RequestedSubject = "auto"
    audience_description: str = Field(default="", max_length=500)
    audience_level: Literal["auto", "introductory", "intermediate", "advanced"] = "auto"
    presentation_forms: list[PresentationForm] = Field(default_factory=list, max_length=4)
    core_message: str = Field(default="", max_length=500)
    viewer_takeaway: str = Field(default="", max_length=500)

    @model_validator(mode="before")
    @classmethod
    def migrate_knowledge(cls, value):
        # Exact legacy value migration, not prompt classification or keyword routing.
        if isinstance(value, dict) and value.get("intent") == "knowledge":
            value = {**value, "intent": "auto"}
            if value.get("subject_kind", "auto") == "auto":
                value["subject_kind"] = "knowledge"
        return value

    @model_validator(mode="after")
    def independent_dimensions(self):
        validate_selections(self.intent, self.secondary_intents, self.presentation_forms)
        return self


def validate_selections(intent, secondary, forms):
    if len(set(secondary)) != len(secondary) or intent in secondary:
        raise ValueError("Secondary purposes must be distinct from each other and the primary purpose")
    if len(set(forms)) != len(forms):
        raise ValueError("Presentation forms must be unique")


class NarrativeBeat(EditorialModel):
    function: BeatFunction
    purpose: str = Field(min_length=1, max_length=500)
    scene_ids: list[str] = Field(min_length=1, max_length=32)


class ContentStrategy(EditorialModel):
    taxonomy_version: Literal["1.0"] = "1.0"
    intent: ContentIntent
    secondary_intents: list[ContentIntent] = Field(default_factory=list, max_length=2)
    subject_kind: ContentSubject
    audience_description: str = Field(min_length=1, max_length=500)
    audience_level: AudienceLevel
    presentation_forms: list[PresentationForm] = Field(min_length=1, max_length=4)
    rationale: str = Field(min_length=1, max_length=1000)
    success_criteria: list[str] = Field(min_length=1, max_length=6)
    outline: list[NarrativeBeat] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def unique_selections(self):
        validate_selections(self.intent, self.secondary_intents, self.presentation_forms)
        if any(not s.strip() or len(s) > 500 for s in self.success_criteria):
            raise ValueError("Success criteria must be nonempty and bounded")
        return self


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
    # None keeps historic plans readable; new native creator plans must resolve this.
    strategy: ContentStrategy | None = None


class ViewerDisclosure(EditorialModel):
    text: str = Field(min_length=1, max_length=100)
    start_seconds: float = Field(default=0, ge=0, le=180)
    end_seconds: float = Field(default=4, gt=0, le=180)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Disclosure end must follow its start")
        return self
