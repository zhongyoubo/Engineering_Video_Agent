"""Measured semantic state compiler; no evaluation of source or expressions."""

from ..semantic_scene import CompiledSemanticEvent
from .motion import resolve_events
from .timeline import TimelineConflict

ALLOWED = {
    "pending": {"running", "awaiting_confirmation", "cancelled"},
    "running": {"succeeded", "failed", "awaiting_confirmation", "cancelled"},
    "failed": {"running", "cancelled"},
    "awaiting_confirmation": {"succeeded", "rejected", "cancelled"},
    "succeeded": {"running"},
    "rejected": set(),
    "cancelled": set(),
}


def compile_semantics(scene, words, fps, allow_estimated=False):
    scene.compiled_semantic_events = []
    if not scene.semantic_scene:
        return
    resolved = resolve_events(scene, scene.semantic_scene.events, words, fps, allow_estimated)
    times = {e.id: (start, end) for e, start, end, _ in resolved}
    entities = {e.id: e for e in scene.semantic_scene.entities}
    states = {e.id: e.state for e in scene.semantic_scene.entities}
    lengths = {e.id: len(e.items) for e in scene.semantic_scene.entities}
    texts = {e.id: len(e.text) for e in scene.semantic_scene.entities}
    last = {}
    compiled = []
    for e, start, end, source in sorted(resolved, key=lambda r: (r[1], r[0].id)):
        if any(times[d][1] > start for d in e.depends_on):
            raise TimelineConflict("Semantic event precedes its prerequisite")
        if e.action != "highlight":
            if last.get(e.target, -1) > start:
                raise TimelineConflict("Conflicting semantic changes overlap")
            last[e.target] = end
            if end >= scene.frames:
                raise TimelineConflict("Visible result needs a held result frame")
        if e.action == "transform":
            entity = entities[e.target]
            if entity.bind_to and any(v is not None for v in [e.x, e.y, e.scale, e.rotation]):
                raise TimelineConflict("Screen-bound transforms must change opacity only")
            if (e.x if e.x is not None else entity.x) + entity.width > 1720 or (
                e.y if e.y is not None else entity.y
            ) + entity.height > 650:
                raise TimelineConflict("Transform destination exceeds semantic stage")
        if e.action == "transition":
            if states[e.target] != e.from_state or e.to_state not in ALLOWED[e.from_state]:
                raise TimelineConflict("Invalid semantic state transition")
            states[e.target] = e.to_state
        if e.action in {"replace", "transition"}:
            if e.items:
                lengths[e.target] = len(e.items)
            if e.text is not None:
                texts[e.target] = len(e.text)
        if e.action == "append":
            lengths[e.target] += len(e.items)
            texts[e.target] += len(e.text or "")
            if lengths[e.target] > 12 or texts[e.target] > 600:
                raise TimelineConflict("Semantic content exceeds visible budget")
        if e.action == "select" and e.selected >= lengths[e.target]:
            raise TimelineConflict("Selection outside actual items")
        compiled.append(
            CompiledSemanticEvent(**e.model_dump(), start_frame=start, end_frame=end, timing_source=source)
        )
    scene.compiled_semantic_events = compiled


def semantic_text(scene):
    if not scene.semantic_scene:
        return ""
    values = [scene.semantic_scene.viewer_question]
    for e in scene.semantic_scene.entities:
        values.extend([e.title, e.text, *[i.text + i.detail for i in e.items]])
    for e in scene.semantic_scene.events:
        values.extend([e.text or "", *[i.text + i.detail for i in e.items]])
    return "".join(values)
