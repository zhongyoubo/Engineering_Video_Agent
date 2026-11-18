"""Compile narration anchors into measured scene-local frames; never execute specifications."""

import re
from ..specs import CompiledEvent
from .timeline import TimelineConflict


def normalize(text):
    return re.sub(r"[\W_]+", "", text).lower()


def resolve_events(scene, events, words, fps, allow_estimated=False):
    if not events:
        return []
    text = normalize(scene.narration)
    measured = bool(words)
    if events and not measured and not allow_estimated:
        raise TimelineConflict("Motion anchors require measured narration timing")
    if measured and normalize("".join(w["text"] for w in words)) != text:
        raise TimelineConflict("Motion alignment differs from narration")
    spans, cursor = [], 0
    for w in words:
        length = len(normalize(w["text"]))
        if length:
            spans.append((cursor, cursor + length, w["start"], w["end"]))
            cursor += length
    compiled = []
    for event in events:
        phrase = normalize(event.anchor.phrase)
        if not phrase:
            raise TimelineConflict("Motion anchor must contain spoken characters")
        start = -1
        for _ in range(event.anchor.occurrence):
            start = text.find(phrase, start + 1)
            if start < 0:
                raise TimelineConflict(f"Missing motion phrase: {event.anchor.phrase}")
        if measured:
            overlaps = [s for s in spans if s[0] < start + len(phrase) and s[1] > start]
            second = overlaps[0][2] if event.anchor.edge == "start" else overlaps[-1][3]
        else:
            position = start if event.anchor.edge == "start" else start + len(phrase)
            second = position / max(1, len(text)) * scene.frames / fps
        first = round((second + event.anchor.offset_ms / 1000) * fps)
        last = first + max(1, round(event.duration_ms / 1000 * fps))
        if first < 0 or last > scene.frames:
            raise TimelineConflict(f"Motion event {event.id} exceeds scene frame budget")
        compiled.append((event, first, last, "measured_words" if measured else "estimated_draft"))
    return compiled


def compile_motion(scene, words, fps, allow_estimated=False):
    from .visuals import compile_visual_scene

    from .semantics import compile_semantics

    candidate = scene.model_copy(deep=True)
    try:
        compile_semantics(candidate, words, fps, allow_estimated)
        compile_visual_scene(candidate, words, fps, allow_estimated)
        legacy = [
            CompiledEvent(
                id=event.id,
                target=event.target,
                action=event.action,
                start_frame=first,
                end_frame=last,
                timing_source=source,
            )
            for event, first, last, source in resolve_events(
                candidate, candidate.motion.events if candidate.motion else [], words, fps, allow_estimated
            )
        ]
    except ValueError:
        scene.compiled_semantic_events = []
        scene.compiled_object_events = []
        scene.compiled_events = []
        raise
    scene.compiled_semantic_events = candidate.compiled_semantic_events
    scene.compiled_object_events = candidate.compiled_object_events
    scene.compiled_events = legacy
