"""Data-only objects, ports, signals and narration-bound actions. No code or URLs."""

from typing import Literal
from pydantic import Field, model_validator
from .specs import Spec, CueAnchor

ObjectKind = Literal[
    "tv",
    "monitor",
    "laptop",
    "console",
    "player",
    "soundbar",
    "speaker",
    "remote",
    "phone",
    "server",
    "router",
]
SceneAction = Literal[
    "reveal", "connect", "signal", "power_on", "power_off", "play", "sound", "press", "volume", "highlight"
]
SoundPreset = Literal["connect", "click", "notify"]


class ObjectPort(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    side: Literal["left", "right", "top", "bottom"]
    position: float = Field(default=0.5, ge=0.1, le=0.9)
    label: str = Field(default="", max_length=20)
    kind: Literal["hdmi", "network", "wireless", "generic"] = "hdmi"


class SceneObject(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    kind: ObjectKind
    label: str = Field(min_length=1, max_length=40)
    x: float = Field(ge=0, le=1650)
    y: float = Field(ge=0, le=530)
    width: float = Field(ge=70, le=1200)
    height: float = Field(ge=70, le=600)
    color: str = Field(default="#173e42", pattern=r"^#[0-9a-fA-F]{6}$")
    powered: bool = True
    screen: Literal["landscape", "game", "stream", "pixels", "black"] = "landscape"
    playback: Literal["smooth", "stepped"] = "smooth"
    hdr: bool = False
    ports: list[ObjectPort] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def bounds(self):
        if self.x + self.width > 1720 or self.y + self.height > 560:
            raise ValueError("Objects must fit the 1720x560 stage, with label space below")
        if len({p.id for p in self.ports}) != len(self.ports):
            raise ValueError("Object port IDs must be unique")
        return self


class SceneConnection(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    source: str = Field(max_length=60)
    source_port: str = Field(max_length=40)
    target: str = Field(max_length=60)
    target_port: str = Field(max_length=40)
    label: str = Field(default="", max_length=40)
    kind: Literal["cable", "wireless"] = "cable"
    connected: bool = True


class ObjectEvent(Spec):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    target: str = Field(max_length=60)
    action: SceneAction
    anchor: CueAnchor
    duration_ms: int = Field(default=900, ge=100, le=12000)
    channel: Literal["video", "audio", "control", "data"] = "video"
    reverse: bool = False
    value: float = Field(default=1, ge=0, le=1)
    depends_on: list[str] = Field(default_factory=list, max_length=4)
    sound: SoundPreset | None = None


class VisualScene(Spec):
    schema_version: Literal["1.0"] = "1.0"
    purpose: str = Field(min_length=5, max_length=500)
    setting: Literal["studio", "living_room", "desktop"] = "studio"
    objects: list[SceneObject] = Field(min_length=1, max_length=10)
    connections: list[SceneConnection] = Field(default_factory=list, max_length=12)
    events: list[ObjectEvent] = Field(default_factory=list, max_length=32)
    sound_enabled: bool = False
    sound_volume: float = Field(default=0.18, ge=0, le=0.35)

    @model_validator(mode="after")
    def references(self):
        objects = {o.id: o for o in self.objects}
        connections = {c.id: c for c in self.connections}
        events = {e.id: e for e in self.events}
        if (
            len(objects) != len(self.objects)
            or len(connections) != len(self.connections)
            or objects.keys() & connections.keys()
        ):
            raise ValueError("Object and connection IDs must be unique and disjoint")
        for c in self.connections:
            if c.source == c.target or c.source not in objects or c.target not in objects:
                raise ValueError("Connections require two different existing objects")
            if c.source_port not in {p.id for p in objects[c.source].ports} or c.target_port not in {
                p.id for p in objects[c.target].ports
            }:
                raise ValueError("Connection endpoints must name actual object ports")
        if len(events) != len(self.events):
            raise ValueError("Object event IDs must be unique")
        for e in self.events:
            required = connections if e.action in {"connect", "signal"} else objects
            if e.target not in required:
                raise ValueError("Action target has the wrong object/connection type")
            if len(set(e.depends_on)) != len(e.depends_on) or any(
                d not in events or d == e.id for d in e.depends_on
            ):
                raise ValueError("Event dependencies must reference other distinct events")
        visited = set()

        def walk(id, seen):
            if id in seen:
                raise ValueError("Event dependencies cannot form a cycle")
            if id in visited:
                return
            for dep in events[id].depends_on:
                walk(dep, seen | {id})
            visited.add(id)

        for id in events:
            walk(id, set())
        return self


class CompiledObjectEvent(Spec):
    id: str
    target: str
    action: SceneAction
    channel: Literal["video", "audio", "control", "data"]
    reverse: bool
    value: float = Field(ge=0, le=1)
    sound: SoundPreset | None
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    timing_source: Literal["measured_words", "estimated_draft"]

    @model_validator(mode="after")
    def range(self):
        if self.end_frame <= self.start_frame:
            raise ValueError("Object action duration must be positive")
        return self


def visual_scene_guidance():
    return {
        "objects": list(ObjectKind.__args__),
        "actions": list(SceneAction.__args__),
        "stage": {"width": 1720, "object_bottom": 560, "label_bottom": 650},
        "planning": "Choose actual objects, setting, ports, initial states, action, observable result and a narration anchor semantically. A TV must look like a TV; picture playback, audio waves and control pulses must be distinguishable. Do not map nouns to graph boxes by keyword. Combine objects and actions; arbitrary TSX remains available for unsupported subjects, never substitute a mislabeled stock device.",
        "connections": "Name actual object ports. connect reveals the cable and plug; signal transports video/audio/control/data along it. reverse changes direction, including TV-to-soundbar audio return. Connect before signal; dependencies must finish before the dependent event starts.",
        "timing": "Events use actual narrated phrases and measured word boundaries. State actions persist; signals/sound/press are transient. Duration must fit actual scene budget. Report illustrative motion as illustration, never a measured frame rate, HDR benchmark or electrical waveform.",
        "sound": "Optional connect/click/notify Foley is quiet, original and synthetic; it illustrates an interaction, not physical HDMI signal sound. Keep speech primary. No inference from decorative waves.",
    }
