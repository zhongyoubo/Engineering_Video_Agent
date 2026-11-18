"""Versioned, data-only native-agent output; never executes generated source."""

from pydantic import Field
from ..domain import StrictModel, Scene, SceneType, StoryboardIR, Diagram
from ..specs import SceneSpec
from ..editorial import SceneRole, ViewerDisclosure, EditorialPlan
from ..visual_scene import VisualScene


class DesignedScene(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    type: SceneType
    title: str = Field(min_length=1, max_length=90)
    subtitle: str = Field(max_length=320)
    narration: str = Field(min_length=1, max_length=3200)
    bullets: list[str] = Field(max_length=6)
    code: str = Field(max_length=1400)
    claim_ids: list[str] = Field(max_length=20)
    evidence_ids: list[str] = Field(max_length=20)
    duration: float = Field(ge=2, le=180)
    diagram: Diagram | None
    motion: SceneSpec | None = None
    visual_scene: VisualScene | None = None
    role: SceneRole = "content"
    message: str = Field(default="", max_length=500)
    viewer_question: str = Field(default="", max_length=500)
    disclosures: list[ViewerDisclosure] = Field(default_factory=list, max_length=4)


class AgentDesign(StrictModel):
    protocol: str = Field(pattern=r"^1\.0$")
    scenes: list[DesignedScene] = Field(min_length=1, max_length=32)
    editorial: EditorialPlan | None = None


def strict_schema():
    """Codex structured output requires required keys on every object."""
    schema = AgentDesign.model_json_schema()

    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return schema


def validate_design(payload, content, brief):
    result = AgentDesign.model_validate(payload)
    claim_ids = {c.id for c in content.claims}
    evidence_ids = {e.id for e in content.evidence}
    scenes = []
    for item in result.scenes:
        if set(item.claim_ids) - claim_ids or set(item.evidence_ids) - evidence_ids:
            raise ValueError("Native Agent returned unknown evidence references")
        if content.kind == "source" and not (item.claim_ids or item.evidence_ids):
            raise ValueError("Source explanations must reference supplied evidence")
        scenes.append(
            Scene(**item.model_dump(), verification="static" if content.kind == "source" else "concept")
        )
    return StoryboardIR(
        title=brief.title,
        language=brief.language,
        accent=brief.accent,
        audience=brief.audience,
        width=brief.render_profile.width,
        height=brief.render_profile.height,
        design_pack=brief.design_pack,
        presentation_profile=brief.presentation_profile,
        creator_brand=brief.creator_brand,
        editorial=result.editorial,
        editorial_request=brief.editorial,
        scenes=scenes,
        notices=[f"{brief.agent_engine} 原生 Agent 生成；尚未自动认定为运行验证。"],
    )


def merge_scene_design(existing, proposed, scene_id):
    """Apply exactly one scene; preserve all other scenes and unchanged audio."""
    if len(proposed.scenes) != 1 or proposed.scenes[0].id != scene_id:
        raise ValueError("Native edit must return exactly the requested scene")
    result = StoryboardIR.model_validate(existing.model_dump())
    prior = next((s for s in result.scenes if s.id == scene_id), None)
    if not prior or prior.locked:
        raise ValueError("Cannot change a missing or locked scene")
    patch = proposed.scenes[0].model_dump()
    patch.update(
        duration=prior.duration,
        start_frame=prior.start_frame,
        frames=prior.frames,
        media_id=prior.media_id,
        media_kind=prior.media_kind,
    )
    if patch["narration"] == prior.narration:
        patch.update(audio_id=prior.audio_id, cues=[c.model_dump() for c in prior.cues])
    result.scenes = [Scene.model_validate(patch) if s.id == scene_id else s for s in result.scenes]
    return result
