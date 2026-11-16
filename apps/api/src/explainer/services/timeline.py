"""Constraint-based frame allocation; never truncate speech to satisfy an impossible duration."""

import math
from ..domain import Cue


class TimelineConflict(ValueError):
    pass


def allocate(board, audio, brief):
    fps = board.fps
    by_id = {a["scene_id"]: a for a in audio}
    padding = math.ceil(0.45 * fps)
    minimum = []
    for scene in board.scenes:
        speech = math.ceil(by_id[scene.id]["duration"] * fps) if by_id[scene.id].get("audio_id") else 0
        length = max(2 * fps, speech + padding) if speech else max(2 * fps, round(scene.duration * fps))
        if scene.locked:
            if speech + padding > scene.frames:
                raise TimelineConflict(f"锁定场景 {scene.id} 无法容纳完整旁白")
            length = scene.frames
        minimum.append(length)
    target = brief.target_seconds * fps
    total = sum(minimum)
    if brief.duration_mode in {"exact", "max"} and total > target:
        # Video-only scenes may shrink to two seconds. Audio speed is handled before allocation.
        flexible = [i for i, s in enumerate(board.scenes) if not s.locked and not by_id[s.id].get("audio_id")]
        for i in flexible:
            reduction = min(minimum[i] - 2 * fps, total - target)
            minimum[i] -= reduction
            total -= reduction
        if total > target:
            raise TimelineConflict(
                f"完整旁白与锁定画面至少需要 {total / fps:.2f} 秒，目标 {target / fps:.2f} 秒；请精简脚本或放宽约束"
            )
    if brief.duration_mode == "exact" and total < target:
        candidates = [i for i, s in enumerate(board.scenes) if not s.locked]
        if not candidates:
            raise TimelineConflict("全部场景已锁定，不能增加停留时间")
        extra = target - total
        while extra:
            available = [i for i in candidates if minimum[i] < 180 * fps]
            if not available:
                raise TimelineConflict("场景最大时长不足以满足目标")
            portion = max(1, extra // len(available))
            for i in available:
                add = min(portion, extra, 180 * fps - minimum[i])
                minimum[i] += add
                extra -= add
                if not extra:
                    break
    cursor = 0
    for scene, frames in zip(board.scenes, minimum):
        scene.start_frame = cursor
        scene.frames = frames
        scene.duration = frames / fps
        cursor += frames
    board.total_frames = cursor
    if brief.duration_mode == "exact" and cursor != target:
        raise TimelineConflict("Exact frame allocation failed")
    return board


def required_tempo(board, audio, brief):
    if brief.duration_mode == "target":
        return 1.0
    by_id = {a["scene_id"]: a for a in audio}
    fixed = 0
    movable = 0
    audio_count = 0
    for scene in board.scenes:
        a = by_id[scene.id]
        if scene.locked:
            fixed += scene.frames / board.fps
        elif a.get("audio_id"):
            movable += a["duration"]
            audio_count += 1
        else:
            fixed += 2
    remaining = brief.target_seconds - fixed - 0.5 * audio_count
    if not movable:
        return 1.0
    if remaining <= 0:
        raise TimelineConflict("锁定内容已占满目标时长")
    tempo = max(1.0, movable / remaining)
    if tempo > brief.max_tempo:
        raise TimelineConflict(f"需要 {tempo:.2f} 倍语速，超过允许的 {brief.max_tempo:.2f}；不能截断旁白")
    return tempo


def word_cues(words, language):
    cues = []
    group = []
    limit = 30 if language == "zh-CN" else 72
    for word in words:
        if group and (
            len("".join(w["text"] for w in group)) + len(word["text"]) > limit
            or word["end"] - group[0]["start"] > 6
        ):
            cues.append(
                Cue(
                    start=group[0]["start"],
                    end=group[-1]["end"],
                    text="".join(w["text"] for w in group).strip(),
                )
            )
            group = []
        group.append(word)
    if group:
        cues.append(
            Cue(start=group[0]["start"], end=group[-1]["end"], text="".join(w["text"] for w in group).strip())
        )
    return cues
