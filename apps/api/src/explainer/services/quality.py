import json
from ..domain import Finding


def inspect(board, content, runtime, audio, requested_seconds):
    findings = []
    claims = {c.id for c in content.claims}
    evidence = {e.id for e in content.evidence}
    cursor = 0
    for s in board.scenes:
        if s.start_frame != cursor:
            findings.append(
                Finding(code="TIMELINE_GAP", severity="error", message="时间线不连续", scene_id=s.id)
            )
        cursor += s.frames
        if set(s.claim_ids) - claims or set(s.evidence_ids) - evidence:
            findings.append(
                Finding(
                    code="UNKNOWN_EVIDENCE", severity="error", message="场景引用不存在的证据", scene_id=s.id
                )
            )
        if s.verification == "runtime" and runtime.get("state") != "observed":
            findings.append(
                Finding(code="FALSE_RUNTIME", severity="error", message="没有真实运行记录", scene_id=s.id)
            )
        if len(s.title) > 40 or any(len(b) > 85 for b in s.bullets):
            findings.append(
                Finding(
                    code="READABILITY_REVIEW",
                    severity="warning",
                    message="文字较长，建议审阅关键帧",
                    scene_id=s.id,
                )
            )
        if any(a.get("engine") == "none" for a in audio if a["scene_id"] == s.id):
            findings.append(
                Finding(
                    code="NO_NARRATION_AUDIO",
                    severity="warning",
                    message="本场景为字幕版，未生成声音",
                    scene_id=s.id,
                )
            )
    if cursor != board.total_frames:
        findings.append(Finding(code="FRAME_TOTAL", severity="error", message="总帧数不一致"))
    if abs(cursor / 30 - requested_seconds) > max(10, requested_seconds * 0.25):
        findings.append(
            Finding(
                code="DURATION_TARGET", severity="warning", message="实际时长与目标不同；优先保留完整旁白"
            )
        )
    if board.audio_alignment in {"estimated_sentence", "mixed", "none"}:
        findings.append(
            Finding(
                code="ESTIMATED_CAPTIONS",
                severity="warning",
                message="存在估计字幕；严格场景可启用 require_alignment 或 stable-ts 对齐器",
            )
        )
    if runtime.get("state") in {"unavailable", "failed"}:
        findings.append(Finding(code="RUNTIME_FALLBACK", severity="warning", message=runtime["message"]))
    if any(a.get("engine") == "espeak" for a in audio):
        findings.append(
            Finding(
                code="DEVELOPMENT_VOICE",
                severity="info",
                message="本地 eSpeak 是开发音色；正式讲解建议配置 Qwen3-TTS",
            )
        )
    return {
        "schema_version": "1.0",
        "checks": ["timeline", "evidence_refs", "runtime_truth", "audio_presence", "readability"],
        "findings": [f.model_dump() for f in findings],
        "runtime": {k: v for k, v in runtime.items() if not k.endswith("_path")},
        "duration": cursor / 30,
        "source_kind": content.kind,
        "alignment": board.audio_alignment,
        "limitations": [
            "静态结构不是运行调用图。",
            "语义真实性和听感仍需人工审阅。",
            "几何溢出仅做基础规则检查。",
        ],
    }


def inspect_video(path, runner, frames):
    metadata = json.loads(
        runner.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    )
    stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    if (stream["width"], stream["height"], int(stream.get("nb_frames", 0))) != (1920, 1080, frames):
        raise ValueError("Rendered media metadata mismatch")
    runner.run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"], timeout=300)
    return {
        "decode": "passed",
        "width": 1920,
        "height": 1080,
        "frames": frames,
        "duration": float(metadata["format"]["duration"]),
    }
