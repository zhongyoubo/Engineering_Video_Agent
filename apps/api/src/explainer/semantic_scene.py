"""Versioned data-only software concepts, state changes and screen bindings."""

from typing import Literal
from pydantic import Field, model_validator
from .specs import Spec, CueAnchor

Component = Literal[
    "PromptInput",
    "Conversation",
    "TokenSequence",
    "ContextWindow",
    "DocumentChunks",
    "RetrievalResults",
    "ModelBoundary",
    "ToolCall",
    "TaskState",
    "EvidenceStack",
    "ApprovalGate",
    "CodeWorkspace",
    "AssetImage",
]
State = Literal["pending", "running", "succeeded", "failed", "awaiting_confirmation", "rejected", "cancelled"]


class SemanticItem(Spec):
    text: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=180)
    active: bool = False


class SemanticEntity(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    component: Component
    title: str = Field(min_length=1, max_length=60)
    text: str = Field(default="", max_length=600)
    items: list[SemanticItem] = Field(default_factory=list, max_length=12)
    state: State = "pending"
    x: float = Field(default=0, ge=0, le=1520)
    y: float = Field(default=0, ge=0, le=530)
    width: float = Field(default=520, ge=180, le=1720)
    height: float = Field(default=400, ge=120, le=650)
    bind_to: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    asset_key: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    provenance: Literal["illustrative", "observed"] = "illustrative"
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def valid(self):
        if self.x + self.width > 1720 or self.y + self.height > 650:
            raise ValueError("Semantic entity is outside its stage")
        if self.component == "AssetImage" and not self.asset_key:
            raise ValueError("AssetImage requires a registered asset key")
        if self.component != "AssetImage" and self.asset_key:
            raise ValueError("Only AssetImage can display an asset")
        if self.provenance == "observed" and not self.evidence_ids:
            raise ValueError("Observed UI requires evidence references")
        return self


class SemanticEvent(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    target: str = Field(max_length=60)
    action: Literal["transition", "replace", "append", "select", "highlight"]
    anchor: CueAnchor
    duration_ms: int = Field(default=700, ge=100, le=4000)
    depends_on: list[str] = Field(default_factory=list, max_length=4)
    from_state: State | None = None
    to_state: State | None = None
    text: str | None = Field(default=None, max_length=600)
    items: list[SemanticItem] = Field(default_factory=list, max_length=12)
    selected: int | None = Field(default=None, ge=0, le=11)

    @model_validator(mode="after")
    def payload(self):
        if self.action == "transition":
            if not self.from_state or not self.to_state or self.from_state == self.to_state:
                raise ValueError("Transition requires two different explicit states")
        elif self.from_state or self.to_state:
            raise ValueError("Only transition changes execution state")
        if self.action == "select" and self.selected is None:
            raise ValueError("Selection requires an item index")
        if self.action != "select" and self.selected is not None:
            raise ValueError("Only selection carries an item index")
        if self.action in {"replace", "append"} and self.text is None and not self.items:
            raise ValueError("Content changes require visible content")
        if self.action in {"highlight", "select"} and (self.text is not None or self.items):
            raise ValueError("Highlight/selection cannot replace content")
        return self


class SemanticExpectation(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    event_id: str
    visible_result: str = Field(min_length=4, max_length=400)


class SemanticScene(Spec):
    schema_version: Literal["1.0"] = "1.0"
    viewer_question: str = Field(min_length=4, max_length=400)
    entities: list[SemanticEntity] = Field(min_length=1, max_length=8)
    events: list[SemanticEvent] = Field(default_factory=list, max_length=16)
    expectations: list[SemanticExpectation] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def references(self):
        ids = {e.id for e in self.entities}
        events = {e.id: e for e in self.events}
        bound = [e.bind_to for e in self.entities if e.bind_to]
        if len(ids) != len(self.entities) or len(events) != len(self.events) or len(bound) != len(set(bound)):
            raise ValueError("Semantic IDs and screen bindings must be unique")
        for e in self.events:
            if (
                e.target not in ids
                or len(e.depends_on) != len(set(e.depends_on))
                or any(d not in events or d == e.id for d in e.depends_on)
            ):
                raise ValueError("Invalid semantic target/dependency")
        done = set()

        def walk(id, seen):
            if id in seen:
                raise ValueError("Semantic dependencies must be acyclic")
            if id in done:
                return
            for d in events[id].depends_on:
                walk(d, seen | {id})
            done.add(id)

        for id in events:
            walk(id, set())
        if len({x.id for x in self.expectations}) != len(self.expectations) or any(
            x.event_id not in events for x in self.expectations
        ):
            raise ValueError("Invalid semantic expectation")
        required = {e.id for e in self.events if e.action != "highlight"}
        if not required.issubset({x.event_id for x in self.expectations}):
            raise ValueError("Every causal semantic event requires a visible-result expectation")
        return self


class CompiledSemanticEvent(SemanticEvent):
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    timing_source: Literal["measured_words", "estimated_draft"]

    @model_validator(mode="after")
    def positive_range(self):
        if self.end_frame <= self.start_frame:
            raise ValueError("Semantic event range must be positive")
        return self


class VisualIntent(Spec):
    viewer_question: str = Field(min_length=4, max_length=400)
    representation: Literal["semantic", "physical", "capture", "mixed"]
    rationale: str = Field(min_length=10, max_length=600)
    visible_result: str = Field(min_length=4, max_length=400)


class AssetRequirement(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    purpose: str = Field(min_length=5, max_length=400)
    provider: Literal["component_svg", "image_service"] = "component_svg"
    title: str = Field(min_length=1, max_length=60)
    items: list[SemanticItem] = Field(min_length=1, max_length=8)


def semantic_guidance():
    return dict(
        components=list(Component.__args__),
        states=list(State.__args__),
        instruction="Choose software concepts and UI by explanatory purpose, not noun keywords or hardware metaphors. semantic_scene composes with visual_scene through bind_to device screen surfaces. Events are measured narration anchors with explicit visible-result expectations. Illustrative data is not actual tool execution. Generated assets require mediated request_assets; inspect their real receipt. Image service is unavailable unless explicitly implemented/configured. Custom SVG/TSX remains available under existing isolation.",
    )
