"""Custom source assets and measured custom motions; no source evaluation on the host."""

import hashlib
import json
from ..creative_scene import CompiledCreativeEvent
from .motion import resolve_events
from .timeline import TimelineConflict


def compile_creative(scene, words, fps, allow_estimated=False):
    scene.compiled_creative_events = []
    if not scene.creation:
        return
    resolved = resolve_events(scene, scene.creation.events, words, fps, allow_estimated)
    times = {e.id: (start, end) for e, start, end, _ in resolved}
    ends = {}
    for event, start, end, source in sorted(resolved, key=lambda r: (r[1], r[0].id)):
        if end >= scene.frames:
            raise TimelineConflict("Creative motion needs a held result frame")
        if any(times[d][1] > start for d in event.depends_on):
            raise TimelineConflict("Creative motion precedes its prerequisite")
        key = (event.target, event.channel)
        if ends.get(key, -1) > start:
            raise TimelineConflict("Overlapping creative changes on the same target/channel")
        ends[key] = end
        scene.compiled_creative_events.append(
            CompiledCreativeEvent(
                **event.model_dump(), start_frame=start, end_frame=end, timing_source=source
            )
        )


def source_manifest(workspace):
    from .engineering.workspace import EngineeringError, source_path

    props = json.loads((workspace.project / "props.json").read_text())
    sources = {}
    scenes = []
    for scene in props.get("scenes", []):
        creation = scene.get("creation")
        if not creation:
            continue
        paths = {
            creation["scene_source"],
            *[e["source_file"] for e in creation["elements"] if e.get("source_file")],
        }
        for name in paths:
            source_path(name)
            if name not in workspace.state["files"]:
                raise EngineeringError("Author the planned scene/material source before build: " + name)
            path = workspace.project / name
            if not path.is_file() or path.is_symlink() or path.read_text() != workspace.state["files"][name]:
                raise EngineeringError("Creative source differs from the tracked authoring state")
            sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = {e["id"] for e in creation.get("events", [])}
        compiled = scene.get("compiled_creative_events", [])
        if {e["id"] for e in compiled} != expected:
            raise EngineeringError("Compile every creative motion from narration before build")
        if any(e["end_frame"] >= scene["frames"] for e in compiled):
            raise EngineeringError("Creative motion exceeds current scene frames")
        scenes.append(dict(scene_id=scene["id"], **creation, compiled_events=compiled))
    return dict(
        schema_version="1.0",
        project_hash=workspace.fingerprint(),
        source_assets=sources,
        scenes=scenes,
        scope="project-owned reusable source; not automatic global library promotion",
    )
