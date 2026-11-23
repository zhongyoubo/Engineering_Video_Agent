"""Versioned data-only software concepts, state changes and screen bindings."""

from typing import Literal
from pydantic import Field, model_validator
from .specs import Spec, CueAnchor
from .spatial_scene import SPATIAL_COMPONENTS, SpatialSpec

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
    "Dial",
    "BranchTree",
    "MetricBar",
    "FlowReservoir",
    "QueueFlow",
    "SpatialCity",
    "QuantityMatrix",
    "NodeNetwork",
]
State = Literal["pending", "running", "succeeded", "failed", "awaiting_confirmation", "rejected", "cancelled"]


class SemanticItem(Spec):
    text: str = Field(min_length=1, max_length=100)
    detail: str = Field(default="", max_length=180)
    active: bool = False


MECHANISMS = {"Dial", "BranchTree", "MetricBar", "FlowReservoir", "QueueFlow"} | SPATIAL_COMPONENTS


class SemanticParameter(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    minimum: float = Field(default=0, ge=-10000, le=10000)
    maximum: float = Field(default=1, ge=-10000, le=10000)
    initial: float = Field(default=0, ge=-10000, le=10000)
    unit: str = Field(default="", max_length=20)

    @model_validator(mode="after")
    def interval(self):
        if not self.minimum < self.maximum or not self.minimum <= self.initial <= self.maximum:
            raise ValueError("Parameter needs an ordered range containing its initial value")
        return self


class SemanticEntity(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    component: Component
    title: str = Field(min_length=1, max_length=60)
    text: str = Field(default="", max_length=600)
    items: list[SemanticItem] = Field(default_factory=list, max_length=12)
    state: State = "pending"
    x: float = Field(default=0, ge=0, le=1520)
    y: float = Field(default=0, ge=0, le=530)
    width: float = Field(default=520, ge=180, le=1920)
    height: float = Field(default=400, ge=120, le=1080)
    bind_to: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    asset_key: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    image_style: Literal["panel", "artwork"] = "panel"
    image_fit: Literal["contain", "cover"] = "contain"
    opacity: float = Field(default=1, ge=0, le=1)
    scale: float = Field(default=1, ge=0.2, le=3)
    rotation: float = Field(default=0, ge=-180, le=180)
    parameter_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    inflow_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    outflow_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    capacity: float = Field(default=100, gt=0, le=1000)
    spatial: SpatialSpec | None = None
    immersive: bool = False
    provenance: Literal["illustrative", "observed"] = "illustrative"
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def valid(self):
        if (self.component in MECHANISMS) != bool(self.parameter_id):
            raise ValueError("Mechanism components require a shared parameter binding only")
        if self.component in {"FlowReservoir", "QueueFlow"}:
            if not self.inflow_id or not self.outflow_id:
                raise ValueError("Flow mechanisms require inflow and outflow rate parameters")
        elif self.inflow_id or self.outflow_id:
            raise ValueError("Only flow mechanisms consume rate bindings")
        if (self.component in SPATIAL_COMPONENTS) != (self.spatial is not None):
            raise ValueError("Spatial components require bounded spatial settings only")
        if self.immersive and (self.component not in SPATIAL_COMPONENTS or self.bind_to):
            raise ValueError("Immersive spatial stages cannot bind a device screen")
        if self.spatial:
            if self.component == "NodeNetwork" and (
                self.spatial.count > 64 or self.spatial.source_node >= self.spatial.count
            ):
                raise ValueError("Network needs at most 64 nodes and a valid source")
            if self.component == "QuantityMatrix" and not self.spatial.asset_keys:
                raise ValueError("Quantity matrix requires registered image assets")
            if self.component != "QuantityMatrix" and self.spatial.asset_keys:
                raise ValueError("Only quantity matrices consume spatial image assets")
            if self.component != "NodeNetwork" and self.spatial.effect_parameter_id:
                raise ValueError("Only networks use a propagation parameter")
        bound_w, bound_h = (1920, 1080) if self.immersive else (1720, 650)
        if self.x + self.width > bound_w or self.y + self.height > bound_h:
            raise ValueError("Semantic entity is outside its stage")
        if self.component == "AssetImage" and not self.asset_key:
            raise ValueError("AssetImage requires a registered asset key")
        if self.component != "AssetImage" and self.asset_key:
            raise ValueError("Only AssetImage can display an asset")
        if self.component != "AssetImage" and self.image_style != "panel":
            raise ValueError("Artwork treatment requires an AssetImage")
        if self.bind_to and (self.scale != 1 or self.rotation != 0):
            raise ValueError("Screen-bound content cannot transform its device surface")
        if self.provenance == "observed" and not self.evidence_ids:
            raise ValueError("Observed UI requires evidence references")
        return self


class SemanticEvent(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    target: str = Field(max_length=60)
    action: Literal["transition", "replace", "append", "select", "highlight", "transform", "parameter"]
    anchor: CueAnchor
    duration_ms: int = Field(default=700, ge=100, le=4000)
    depends_on: list[str] = Field(default_factory=list, max_length=4)
    from_state: State | None = None
    to_state: State | None = None
    text: str | None = Field(default=None, max_length=600)
    items: list[SemanticItem] = Field(default_factory=list, max_length=12)
    selected: int | None = Field(default=None, ge=0, le=11)

    value: float | None = Field(default=None, ge=-10000, le=10000)
    x: float | None = Field(default=None, ge=0, le=1520)
    y: float | None = Field(default=None, ge=0, le=530)
    opacity: float | None = Field(default=None, ge=0, le=1)
    scale: float | None = Field(default=None, ge=0.2, le=3)
    rotation: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def payload(self):
        if (self.action == "parameter") != (self.value is not None):
            raise ValueError("Parameter action requires a numeric destination only")
        if self.action == "parameter" and (self.text is not None or self.items):
            raise ValueError("Parameter changes cannot also replace content")
        transforms = [self.x, self.y, self.opacity, self.scale, self.rotation]
        if (self.action == "transform") != any(v is not None for v in transforms):
            raise ValueError("Transform action requires explicit transform values only")
        if self.action == "transform" and (self.text is not None or self.items):
            raise ValueError("Transform cannot also change content")
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
    background_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    background_asset_key: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    title_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    show_heading: bool = True
    parameters: list[SemanticParameter] = Field(default_factory=list, max_length=8)
    entities: list[SemanticEntity] = Field(min_length=1, max_length=8)
    events: list[SemanticEvent] = Field(default_factory=list, max_length=16)
    expectations: list[SemanticExpectation] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def references(self):
        ids = {e.id for e in self.entities}
        parameters = {p.id: p for p in self.parameters}
        if len(parameters) != len(self.parameters) or ids & parameters.keys():
            raise ValueError("Parameter and entity IDs must be globally distinct within a scene")
        for entity in self.entities:
            for key in [
                entity.parameter_id,
                entity.inflow_id,
                entity.outflow_id,
                entity.spatial.effect_parameter_id if entity.spatial else None,
            ]:
                if key and key not in parameters:
                    raise ValueError("Mechanism references a missing parameter")
            if entity.component in {"FlowReservoir", "QueueFlow"}:
                if not 0 <= parameters[entity.parameter_id].initial <= entity.capacity:
                    raise ValueError("Initial flow stock exceeds capacity")
                if any(parameters[k].minimum < 0 for k in [entity.inflow_id, entity.outflow_id]):
                    raise ValueError("Flow rates must remain nonnegative")
        if any(e.immersive for e in self.entities) and (len(self.entities) != 1 or self.show_heading):
            raise ValueError("Immersive scene needs one entity and show_heading=false")
        events = {e.id: e for e in self.events}
        bound = [e.bind_to for e in self.entities if e.bind_to]
        if len(ids) != len(self.entities) or len(events) != len(self.events) or len(bound) != len(set(bound)):
            raise ValueError("Semantic IDs and screen bindings must be unique")
        for e in self.events:
            if e.action == "parameter" and any(
                entity.component in {"FlowReservoir", "QueueFlow"} and entity.parameter_id == e.target
                for entity in self.entities
            ):
                raise ValueError("Flow stock is integrated from rates; animate its rate parameters instead")
            if (
                e.target not in (parameters if e.action == "parameter" else ids)
                or len(e.depends_on) != len(set(e.depends_on))
                or any(d not in events or d == e.id for d in e.depends_on)
            ):
                raise ValueError("Invalid semantic target/dependency")
            if (
                e.action == "parameter"
                and not parameters[e.target].minimum <= e.value <= parameters[e.target].maximum
            ):
                raise ValueError("Parameter destination exceeds its declared range")
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
    provider: Literal["component_svg", "image_service", "project_image"] = "component_svg"
    title: str = Field(min_length=1, max_length=60)
    items: list[SemanticItem] = Field(default_factory=list, max_length=8)
    image_prompt: str | None = Field(default=None, min_length=20, max_length=2500)
    size: Literal["landscape", "portrait", "square"] = "landscape"
    transparent: bool = False
    project_asset_id: str | None = Field(default=None, pattern=r"^mat_[a-f0-9]{32}$")

    @model_validator(mode="after")
    def provider_payload(self):
        if self.provider == "component_svg" and not self.items:
            raise ValueError("SVG document requires visible rows")
        if (self.provider == "image_service") != (self.image_prompt is not None):
            raise ValueError("Only image_service requires an image prompt")
        if (self.provider == "project_image") != (self.project_asset_id is not None):
            raise ValueError("Only project_image requires a registered project asset ID")
        if self.provider == "component_svg" and self.transparent:
            raise ValueError("SVG document factory does not generate transparent cutouts")
        return self


def semantic_guidance():
    return dict(
        components=list(Component.__args__),
        states=list(State.__args__),
        spatial=dict(
            components=sorted(SPATIAL_COMPONENTS),
            fps=30,
            parameters="SpatialCity camera; QuantityMatrix normalized reveal; NodeNetwork layout plus optional propagation parameter",
            rendering="protected Three.js city and deterministic SVG/Canvas layouts; immutable registered image keys",
            limits="count<=768; networks<=64; immersive is one unbound entity with show_heading=false",
        ),
        instruction="Choose software concepts and UI by explanatory purpose, not noun keywords or hardware metaphors. semantic_scene composes with visual_scene through bind_to device screen surfaces. Events are measured narration anchors with explicit visible-result expectations. Illustrative data is not actual tool execution. Generated assets require mediated request_assets; inspect their real receipt. Use only advertised asset providers. image_service requires an administrator-configured gateway; project_image requires an ID from this project catalog. Image prompts describe recognizable objects, setting, palette, composition, empty text regions and cutouts. Use background_asset_key for full-frame illustration, AssetImage.image_style=artwork for independent unframed elements, and transform events for measured movement/reveal. Use shared numeric parameters and parameter events for Dial, BranchTree and MetricBar linkage. FlowReservoir and QueueFlow integrate declared nonnegative inflow/outflow rates over actual frame time, holding initial stock in parameter_id and bounded by capacity; these are illustrative mechanisms unless evidence establishes observed values. No universal topic template or automatic demo disclaimer. Custom SVG/TSX remains available under existing isolation.",
    )
