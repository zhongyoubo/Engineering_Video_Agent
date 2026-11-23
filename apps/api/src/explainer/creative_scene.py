"""Free subject/scene/motion contracts. Descriptions are data; authored code stays isolated."""

from pathlib import PurePosixPath
from typing import Literal
from pydantic import Field, model_validator
from .specs import Spec, CueAnchor


def authored_path(value):
    p = PurePosixPath(value)
    if (
        str(p) != value
        or p.is_absolute()
        or "\\" in value
        or ":" in value
        or ".." in p.parts
        or not p.parts
        or p.parts[0] != "src"
        or any(part.startswith(".") or part == "node_modules" for part in p.parts)
        or p.suffix not in {".tsx", ".ts"}
    ):
        raise ValueError("Creative source must be a canonical src TS/TSX path")
    return value


class CreativeElement(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    role: Literal["subject", "environment", "prop", "annotation", "camera"]
    description: str = Field(min_length=10, max_length=800)
    implementation: Literal["source", "asset", "capture", "kit"]
    source_file: str | None = Field(default=None, max_length=240)
    asset_key: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,60}$")

    @model_validator(mode="after")
    def binding(self):
        if (self.implementation == "source") != bool(self.source_file):
            raise ValueError("Source elements require their authored source file only")
        if (self.implementation == "asset") != bool(self.asset_key):
            raise ValueError("Image elements require their registered asset key only")
        if self.source_file:
            authored_path(self.source_file)
        return self


class CreativeEvent(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    target: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    channel: str = Field(default="state", pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    anchor: CueAnchor
    duration_ms: int = Field(default=1200, ge=100, le=4000)
    before: str = Field(min_length=5, max_length=500)
    change: str = Field(min_length=5, max_length=500)
    after: str = Field(min_length=5, max_length=500)
    depends_on: list[str] = Field(default_factory=list, max_length=8)


class CreativeScene(Spec):
    visual_goal: str = Field(min_length=10, max_length=800)
    composition: str = Field(min_length=10, max_length=1200)
    palette: list[str] = Field(min_length=2, max_length=8)
    techniques: list[Literal["svg", "canvas", "three", "images", "screen", "diagram"]] = Field(
        min_length=1, max_length=6
    )
    scene_source: str = Field(min_length=5, max_length=240)
    elements: list[CreativeElement] = Field(min_length=1, max_length=24)
    events: list[CreativeEvent] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def references(self):
        import re

        authored_path(self.scene_source)
        if len(set(self.techniques)) != len(self.techniques):
            raise ValueError("Creative techniques must be unique")
        if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in self.palette):
            raise ValueError("Creative palette uses exact six-digit colors")
        ids, events = {e.id for e in self.elements}, {e.id: e for e in self.events}
        if len(ids) != len(self.elements) or len(events) != len(self.events):
            raise ValueError("Creative element/event IDs must be unique")
        if not any(e.role == "subject" for e in self.elements):
            raise ValueError("Creative scene requires a visible subject")
        for event in self.events:
            if event.target not in ids or len(set(event.depends_on)) != len(event.depends_on):
                raise ValueError("Creative motion needs existing targets and unique dependencies")
            if any(d not in events or d == event.id for d in event.depends_on):
                raise ValueError("Creative motion dependency is missing or self-referential")
        visited, active = set(), set()

        def visit(id):
            if id in active:
                raise ValueError("Creative motion dependency cycle")
            if id in visited:
                return
            active.add(id)
            for dep in events[id].depends_on:
                visit(dep)
            active.remove(id)
            visited.add(id)

        for id in events:
            visit(id)
        return self


class CompiledCreativeEvent(CreativeEvent):
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    timing_source: Literal["measured_words", "estimated_draft"]

    @model_validator(mode="after")
    def range(self):
        if self.end_frame <= self.start_frame:
            raise ValueError("Creative event requires a positive frame range")
        return self


def creative_asset_keys(scene):
    value = scene.get("creation") or {}
    return {e["asset_key"] for e in value.get("elements", []) if e.get("asset_key")}


def creative_expectations(props):
    return {
        s["id"] + ":" + kind + ":" + item["id"]
        for s in props.get("scenes", [])
        for kind in ("element", "event")
        for item in (s.get("creation") or {}).get("elements" if kind == "element" else "events", [])
    }


def creative_guidance():
    return dict(
        contract="Every newly planned engineering scene requires creation, including the opening/closing. Start from the audience's question and a concrete visual goal, not a component/topic lookup.",
        materials="Create original recognizable SVG/Canvas/Three source modules as needed. Register source elements with source_file; keep reusable artwork under src/assets and scenes under src/scenes. Use registered image_service/project_image keys for raster art. Preserve identity across shots. A code module is a source material, not a claim of image-model inference.",
        layout="Free authored composition and palette. Existing diagrams/device/semantic/spatial kits are optional tools, not a topic whitelist. Diagram grid/fan limits apply only when selecting the legacy motion spec.",
        motion="Describe before/change/after for every causal event, bind its target/channel and narration phrase, then implement compiled_creative_events through creativeProgress from ./creative-kit. Camera motion is an authored element/channel; declare technique=three for software WebGL. Root owns captions/audio. Use actual frames, not independent animation clocks.",
        review="Inspect every scene:element:id and scene:event:id, actual silhouettes/scene composition and continuous causal changes. Request missing configured services explicitly; never replace an unsupported subject with a mislabeled stock diagram.",
    )
