from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .specs import RenderProfile, VoiceSpec, SceneSpec, CompiledEvent
from .editorial import (
    EditorialBrief,
    EditorialPlan,
    CoverSpec,
    ViewerDisclosure,
    PresentationProfile,
    SceneRole,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SceneType(str, Enum):
    title = "title"
    cards = "cards"
    flow = "flow"
    architecture = "architecture"
    code = "code"
    terminal = "terminal"
    ui = "ui"
    summary = "summary"


class AgentChange(StrictModel):
    scene_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    instruction: str = Field(min_length=1, max_length=3000)


class Brief(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    prompt: str = Field(default="", max_length=12000)
    input_id: str | None = None
    language: Literal["zh-CN", "en-US"] = "zh-CN"
    audience: Literal["general", "developer", "beginner", "executive"] = "general"
    target_seconds: int = Field(default=90, ge=20, le=900)
    duration_mode: Literal["target", "exact", "max"] = "target"
    max_tempo: float = Field(default=1.15, ge=1, le=1.3)
    require_alignment: bool = False
    accent: Literal["blue", "violet", "teal", "amber"] = "blue"
    voice: Literal["auto", "espeak", "qwen", "edge", "ming", "none"] = "auto"
    mode: Literal["automatic", "storyboard"] = "automatic"
    agent_engine: Literal["pipeline", "codex", "claude-code"] = "pipeline"
    agent_change: AgentChange | None = None
    video_mode: Literal["template", "engineering"] = "template"
    quality_profile: Literal["professional", "draft"] = "professional"
    render_profile: RenderProfile = Field(default_factory=RenderProfile)
    voice_spec: VoiceSpec = Field(default_factory=VoiceSpec)
    design_pack: Literal["editorial_warm", "workspace_tech"] = "workspace_tech"
    presentation_profile: PresentationProfile = "creator"
    editorial: EditorialBrief = Field(default_factory=EditorialBrief)
    creator_brand: str = Field(default="", max_length=80)
    runtime: Literal["none", "auto", "static-web", "python-cli", "node-web", "python-api", "node-cli"] = (
        "none"
    )
    runtime_entry: str = Field(default="", max_length=300)
    require_real_demo: bool = False
    runtime_actions: list[dict] = Field(default_factory=list, max_length=24)
    api_requests: list[dict] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def content_required(self):
        if not self.prompt.strip() and not self.input_id:
            raise ValueError("Provide a prompt or source input")
        if self.require_real_demo and (self.runtime == "none" or not self.input_id):
            raise ValueError("Real demo requires source and a runtime adapter")
        if self.video_mode == "engineering":
            if self.agent_engine == "pipeline":
                raise ValueError("Engineering mode requires Codex or Claude Code")
            if self.quality_profile == "professional":
                if self.voice in {"none", "espeak"}:
                    raise ValueError("Professional engineering output requires Qwen, Edge or Ming narration")
                if self.voice == "auto":
                    self.voice = "qwen"
                self.require_alignment = True
        if self.agent_change and self.agent_engine == "pipeline":
            raise ValueError("Native changes require a native Agent engine")
        if self.require_alignment and self.voice == "none":
            raise ValueError("Alignment requires narration audio")
        return self


class Claim(StrictModel):
    id: str
    statement: str
    status: Literal["user_provided", "observed_static", "observed_runtime", "inferred", "hypothetical"]
    evidence_ids: list[str] = Field(default_factory=list)


class Evidence(StrictModel):
    id: str
    path: str
    kind: str
    excerpt: str = Field(max_length=3000)
    sha256: str


class ContentIR(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str
    kind: str
    summary: str
    claims: list[Claim]
    evidence: list[Evidence]
    languages: list[str]
    modules: list[str]
    files_count: int
    warnings: list[str] = Field(default_factory=list)


class Cue(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str


class DiagramNode(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    label: str = Field(min_length=1, max_length=32)
    detail: str = Field(max_length=60)
    x: float = Field(ge=0, le=1460)
    y: float = Field(ge=0, le=460)
    reveal: float = Field(ge=0, le=0.9)
    emphasis: Literal["none", "pulse"]


class DiagramEdge(StrictModel):
    source: str
    target: str
    label: str = Field(max_length=24)
    reveal: float = Field(ge=0, le=0.9)


class Diagram(StrictModel):
    nodes: list[DiagramNode] = Field(min_length=1, max_length=12)
    edges: list[DiagramEdge] = Field(max_length=24)

    @model_validator(mode="after")
    def valid_edges(self):
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes) or any(e.source not in ids or e.target not in ids for e in self.edges):
            raise ValueError("Diagram requires unique nodes and valid edge endpoints")
        return self


class Scene(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    type: SceneType
    title: str = Field(min_length=1, max_length=90)
    subtitle: str = Field(default="", max_length=320)
    narration: str = Field(min_length=1, max_length=3200)
    bullets: list[str] = Field(default_factory=list, max_length=6)
    code: str = Field(default="", max_length=1400)
    claim_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    verification: Literal["user_provided", "static", "runtime", "concept"] = "concept"
    duration: float = Field(default=12, ge=2, le=180)
    start_frame: int = Field(default=0, ge=0)
    frames: int = Field(default=360, ge=1)
    audio_id: str | None = None
    media_id: str | None = None
    media_kind: Literal["image", "video"] = "image"
    cues: list[Cue] = Field(default_factory=list)
    locked: bool = False
    diagram: Diagram | None = None
    motion: SceneSpec | None = None
    compiled_events: list[CompiledEvent] = Field(default_factory=list, max_length=24)
    role: SceneRole = "content"
    message: str = Field(default="", max_length=500)
    viewer_question: str = Field(default="", max_length=500)
    disclosures: list[ViewerDisclosure] = Field(default_factory=list, max_length=4)


class StoryboardIR(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str
    language: Literal["zh-CN", "en-US"]
    accent: Literal["blue", "violet", "teal", "amber"] = "blue"
    audience: str
    scenes: list[Scene] = Field(min_length=1, max_length=32)
    fps: Literal[30] = 30
    width: Literal[1920, 3840] = 1920
    height: Literal[1080, 2160] = 1080
    design_pack: Literal["editorial_warm", "workspace_tech"] = "workspace_tech"
    presentation_profile: PresentationProfile = "creator"
    creator_brand: str = Field(default="", max_length=80)
    cover: CoverSpec | None = None
    editorial: EditorialPlan | None = None
    total_frames: int = Field(default=2700, ge=1)
    notices: list[str] = Field(default_factory=list)
    audio_alignment: Literal["estimated_sentence", "native_words", "forced_words", "mixed", "none"] = "none"

    @model_validator(mode="after")
    def unique_ids(self):
        if (self.width, self.height) not in {(1920, 1080), (3840, 2160)}:
            raise ValueError("Unsupported output aspect ratio")
        if len({s.id for s in self.scenes}) != len(self.scenes):
            raise ValueError("Scene IDs must be unique")
        if any(len(b) > 140 for s in self.scenes for b in s.bullets):
            raise ValueError("Bullet is too long")
        return self


class Finding(StrictModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    scene_id: str | None = None


class CreateProject(StrictModel):
    name: str = Field(min_length=1, max_length=100)


class CreateVideo(StrictModel):
    project_id: str
    brief: Brief


class EngineeringBrief(Brief):
    video_mode: Literal["engineering"] = "engineering"
    agent_engine: Literal["codex", "claude-code"] = "codex"


class CreateEngineeringVideo(StrictModel):
    project_id: str
    brief: EngineeringBrief


class ForkRevision(StrictModel):
    expected_version: int
    storyboard: StoryboardIR | None = None
    brief: Brief | None = None
    auto_render: bool = True
