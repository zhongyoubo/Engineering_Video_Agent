"""Compile and materialize trusted object-scene data; no source evaluation."""

import shutil
from ..config import ROOT
from ..visual_scene import CompiledObjectEvent
from .motion import resolve_events
from .timeline import TimelineConflict


def compile_visual_scene(scene, words, fps, allow_estimated=False):
    scene.compiled_object_events = []
    if not scene.visual_scene:
        return
    if scene.motion or scene.diagram:
        raise TimelineConflict("Choose a visual scene or a diagram/motion layout, not both")
    resolved = resolve_events(scene, scene.visual_scene.events, words, fps, allow_estimated)
    times = {e.id: (first, last) for e, first, last, _ in resolved}
    connections = {c.id: c for c in scene.visual_scene.connections}
    objects = {o.id: o for o in scene.visual_scene.objects}
    compiled = []
    for event, first, last, source in resolved:
        if any(times[dependency][1] > first for dependency in event.depends_on):
            raise TimelineConflict("Object action starts before its prerequisite finishes")
        if event.action == "signal" and not connections[event.target].connected:
            connects = [
                times[e.id][1]
                for e in scene.visual_scene.events
                if e.action == "connect" and e.target == event.target
            ]
            if not connects or min(connects) > first:
                raise TimelineConflict("A signal cannot flow before its cable is connected")
        if event.action in {"play", "sound", "volume"}:
            power = sorted(
                (
                    e
                    for e in scene.visual_scene.events
                    if e.action in {"power_on", "power_off"}
                    and e.target == event.target
                    and times[e.id][0] <= first
                ),
                key=lambda e: times[e.id][0],
            )
            ready = (
                objects[event.target].powered
                if not power
                else power[-1].action == "power_on" and times[power[-1].id][1] <= first
            )
            if not ready:
                raise TimelineConflict("A playback/audio action cannot precede device power-on")
        compiled.append(
            CompiledObjectEvent(
                id=event.id,
                target=event.target,
                action=event.action,
                channel=event.channel,
                reverse=event.reverse,
                value=event.value,
                sound=event.sound,
                start_frame=first,
                end_frame=last,
                timing_source=source,
            )
        )
    scene.compiled_object_events = compiled


def prepare_visual_assets(board, public):
    presets = {
        e.sound
        for s in board.scenes
        if s.visual_scene and s.visual_scene.sound_enabled
        for e in s.compiled_object_events
        if e.sound
    }
    for preset in presets:
        source = ROOT / "assets/sfx" / (preset + ".wav")
        if not source.is_file():
            raise ValueError("Missing original interaction sound preset")
        shutil.copyfile(source, public / ("scene-sfx-" + preset + ".wav"))
    return sorted(presets)
