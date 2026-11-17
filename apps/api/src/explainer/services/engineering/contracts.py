"""Provider-neutral engineering contracts. All edits are mediated source files."""

from typing import Literal
from pydantic import Field, model_validator
from ...domain import StrictModel
from ...adapters.native_contract import AgentDesign
from ...editorial import EditorialPlan


class MotionShot(StrictModel):
    scene_id: str
    visual: str = Field(min_length=10, max_length=1500)
    movement: str = Field(min_length=10, max_length=1500)
    assets: list[str] = Field(max_length=20)


class ProductionPlan(StrictModel):
    objective: str = Field(min_length=10, max_length=1500)
    story_arc: list[str] = Field(min_length=2, max_length=12)
    art_direction: str = Field(min_length=10, max_length=2000)
    voice_direction: str = Field(min_length=10, max_length=1000)
    shots: list[MotionShot] = Field(min_length=1, max_length=32)
    storyboard: AgentDesign
    # Optional only for loading historic saved plans. New creator planning requires it.
    editorial: EditorialPlan | None = None

    @model_validator(mode="after")
    def match_shots(self):
        ids = [scene.id for scene in self.storyboard.scenes]
        if sorted(shot.scene_id for shot in self.shots) != sorted(ids):
            raise ValueError("Every scene requires exactly one visual and motion design")
        if self.storyboard.editorial is not None and self.storyboard.editorial != self.editorial:
            raise ValueError("Storyboard editorial must be null or match the production-plan editorial")
        return self


class SourceEdit(StrictModel):
    path: str = Field(min_length=1, max_length=320)
    content: str = Field(max_length=50000)


class VisualReview(StrictModel):
    accepted: bool
    legibility: int = Field(ge=0, le=5)
    visual_explanation: int = Field(ge=0, le=5)
    timing: int = Field(ge=0, le=5)
    issues: list[str] = Field(max_length=30)
    inspected_frames: list[str] = Field(min_length=1, max_length=128)
    motion_continuity: int = Field(default=0, ge=0, le=5)
    inspected_motion_frames: list[str] = Field(default_factory=list, max_length=32)
    content_focus: int = Field(default=0, ge=0, le=5)
    cover_promise: int = Field(default=0, ge=0, le=5)
    opening_closing: int = Field(default=0, ge=0, le=5)
    viewer_presentation: int = Field(default=0, ge=0, le=5)
    purpose_fulfillment: int = Field(default=0, ge=0, le=5)


class EngineeringAction(StrictModel):
    action: Literal["write_files", "build", "render_preview", "review", "finish"]
    summary: str = Field(min_length=1, max_length=300)
    files: list[SourceEdit] = Field(max_length=30)
    review: VisualReview | None

    @model_validator(mode="after")
    def coherent_action(self):
        if self.action == "write_files" and not self.files:
            raise ValueError("write_files requires source edits")
        if self.action != "write_files" and self.files:
            raise ValueError("Only write_files may modify files")
        if (self.action == "review") != (self.review is not None):
            raise ValueError("Review evidence belongs only to review actions")
        if len({f.path for f in self.files}) != len(self.files):
            raise ValueError("Duplicate source paths")
        return self


def schema(model):
    value = model.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return value
