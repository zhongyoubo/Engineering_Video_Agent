import json
import re
import shutil
import textwrap

import httpx

from ..services.process import ProcessError


def probe(path, runner):
    value = json.loads(
        runner.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    )
    return float(value["format"]["duration"])


def synthesize(scene, language, engine, settings, directory, runner):
    raw, mastered = directory / (scene.id + "-raw.wav"), directory / (scene.id + ".wav")
    selected = engine if engine != "auto" else settings.tts_engine
    if selected == "auto":
        selected = "espeak" if shutil.which("espeak-ng") else "none"
    if selected == "none":
        return {"path": None, "duration": scene.duration, "engine": "none"}
    words = []
    if selected == "espeak":
        if not shutil.which("espeak-ng"):
            return {
                "path": None,
                "duration": scene.duration,
                "engine": "none",
                "warning": "未安装 espeak-ng，输出字幕版。",
            }
        text = directory / (scene.id + ".txt")
        spoken = scene.narration
        text.write_text(spoken)
        try:
            from .espeak_native import synthesize_events

            words = synthesize_events(spoken, language, raw)
        except (OSError, RuntimeError):
            runner.run(
                [
                    "espeak-ng",
                    "-v",
                    "cmn" if language == "zh-CN" else "en-us+m3",
                    "-s",
                    "250" if language == "zh-CN" else "170",
                    "-f",
                    text,
                    "-w",
                    raw,
                ],
                timeout=90,
            )
    elif selected == "edge":
        import asyncio

        import edge_tts

        async def _speak():
            # Cloud Neural voice (Microsoft Edge read-aloud service); mp3 out,
            # mastered to wav by the shared ffmpeg step below.
            com = edge_tts.Communicate(scene.narration, settings.edge_voice)
            await com.save(raw)

        try:
            asyncio.run(_speak())
        except Exception as error:
            raise ProcessError(f"Edge TTS failed: {error}") from error
    elif selected == "ming":
        # Ming-3.0-TTS via its official SGLang-Omni server (OpenAI-compatible
        # /v1/audio/speech). Requires EXPLAINER_MING_URL; fails fast otherwise.
        if not settings.ming_url:
            raise ValueError("Ming TTS 未配置：设置 EXPLAINER_MING_URL 指向 SGLang-Omni 服务")
        headers = {"Authorization": "Bearer " + settings.ming_key} if settings.ming_key else {}
        with httpx.Client(timeout=300, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "POST",
                settings.ming_url.rstrip("/") + "/v1/audio/speech",
                headers=headers,
                json={
                    "model": settings.ming_model,
                    "input": scene.narration,
                    "response_format": "wav",
                },
            ) as response:
                response.raise_for_status()
                size = 0
                with raw.open("wb") as out:
                    for chunk in response.iter_bytes():
                        runner.guard()
                        size += len(chunk)
                        if size > 40 * 1024 * 1024:
                            raise ProcessError("TTS response too large")
                        out.write(chunk)
    elif selected == "qwen":
        headers = {"Authorization": "Bearer " + settings.tts_key} if settings.tts_key else {}
        with httpx.Client(timeout=300, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "POST",
                settings.tts_url.rstrip("/") + "/synthesize",
                headers=headers,
                json={"text": scene.narration, "language": language},
            ) as response:
                response.raise_for_status()
                size = 0
                with raw.open("wb") as out:
                    for chunk in response.iter_bytes():
                        runner.guard()
                        size += len(chunk)
                        if size > 40 * 1024 * 1024:
                            raise ProcessError("TTS response too large")
                        out.write(chunk)
    else:
        raise ValueError("Unsupported voice engine")
    duration = probe(raw, runner)
    if not 0.1 < duration <= 180:
        raise ValueError("Invalid TTS duration")
    runner.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            raw,
            "-af",
            "highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            mastered,
        ],
        timeout=90,
    )
    return {
        "path": str(mastered),
        "duration": probe(mastered, runner),
        "engine": selected,
        "words": words,
        "alignment_method": "native_words" if words else "estimated_sentence",
    }


def estimated_cues(text, duration):
    """Sentence-weighted estimates, intentionally NOT advertised as ASR/forced alignment."""
    chunks = [s.strip() for s in re.split(r"(?<=[。！？.!?；;])", text) if s.strip()]
    pieces = []
    for chunk in chunks:
        if re.search(r"[\u3400-\u9fff]", chunk):
            pieces.extend(chunk[i : i + 40] for i in range(0, len(chunk), 40))
        else:
            pieces.extend(textwrap.wrap(chunk, width=72, break_long_words=False, break_on_hyphens=False))
    weight = sum(max(len(p), 1) for p in pieces) or 1
    now, out = 0.0, []
    for piece in pieces:
        end = now + duration * len(piece) / weight
        out.append({"start": round(now, 4), "end": round(end, 4), "text": piece})
        now = end
    return out
