import json
import re
import shutil
import textwrap
import hashlib

import httpx

from ..services.process import ProcessError
from ..specs import VoiceSpec


QWEN_MAX_TEXT = 1600  # Matches the bundled gateway and isolated infer_worker contract.


class VoiceRequestError(ValueError):
    pass


def validate_voice_text(text, engine):
    if engine == "qwen" and len(text) > QWEN_MAX_TEXT:
        raise VoiceRequestError("Qwen 单场景旁白最多1600个字符；请拆分镜头或精简旁白后重试。")


def voice_configuration(engine, settings, spec=None):
    spec = spec or VoiceSpec()
    selected = engine if engine != "auto" else settings.tts_engine
    if selected == "auto":
        selected = "espeak" if shutil.which("espeak-ng") else "none"
    # Explicitly reject unsupported customization instead of silently ignoring it.
    if selected == "qwen" and (spec.voice_id not in {"", "professional-male"} or spec.model):
        raise ValueError(
            "Qwen clone service uses its configured reference/model; change service revision instead"
        )
    if selected == "ming" and bool(settings.ming_ref_audio) != bool(settings.ming_ref_text):
        raise ValueError("Ming voice cloning requires both configured reference audio and transcript")
    if selected == "ming" and spec.voice_id:
        raise ValueError("Ming adapter does not expose voice selection")
    if selected not in {"ming"} and spec.model:
        raise ValueError("This voice adapter does not expose model selection")
    configuration = {
        "engine": selected,
        "endpoint": settings.ming_url
        if selected == "ming"
        else settings.tts_url
        if selected == "qwen"
        else "",
        "model": spec.model or (settings.ming_model if selected == "ming" else ""),
        "voice_id": spec.voice_id
        or (settings.edge_voice if selected == "edge" else "professional-male" if selected == "qwen" else ""),
        "speed": spec.speed,
        "revision": spec.revision,
        "service_revision": settings.tts_revision,
        "mastering": "highpass65-loudnorm16-peak1.5-lra7-v3",
        "native_timing": "edge-word-boundary-v1" if selected == "edge" else "provider-v1",
    }
    if selected == "ming":
        configuration.update(
            reference_digest=hashlib.sha256(
                json.dumps([settings.ming_ref_audio, settings.ming_ref_text], ensure_ascii=False).encode()
            ).hexdigest(),
            seed=settings.ming_seed,
        )
    return configuration


def voice_cache_key(text, language, engine, settings, spec=None):
    payload = {"text": text, "language": language, **voice_configuration(engine, settings, spec)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def probe(path, runner):
    value = json.loads(
        runner.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    )
    return float(value["format"]["duration"])


def synthesize(scene, language, engine, settings, directory, runner, spec=None):
    raw, mastered = directory / (scene.id + "-raw.wav"), directory / (scene.id + ".wav")
    configuration = voice_configuration(engine, settings, spec)
    selected = configuration["engine"]
    validate_voice_text(scene.narration, selected)
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
            com = edge_tts.Communicate(
                scene.narration,
                configuration["voice_id"],
                boundary="WordBoundary",
                proxy=settings.tts_proxy or None,
            )
            with raw.open("wb") as output:
                async for message in com.stream():
                    runner.guard()
                    if message["type"] == "audio":
                        output.write(message["data"])
                        if output.tell() > 40 * 1024 * 1024:
                            raise ProcessError("TTS response too large")
                    elif message["type"] == "WordBoundary":
                        words.append(
                            {
                                "text": message["text"],
                                "start": message["offset"] / 10_000_000,
                                "end": (message["offset"] + message["duration"]) / 10_000_000,
                            }
                        )

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
        payload = {
            "model": configuration["model"],
            "input": scene.narration,
            "response_format": "wav",
            "seed": settings.ming_seed,
        }
        if settings.ming_ref_audio:
            payload.update(ref_audio=settings.ming_ref_audio, ref_text=settings.ming_ref_text)
        with httpx.Client(timeout=300, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "POST",
                settings.ming_url.rstrip("/") + "/v1/audio/speech",
                headers=headers,
                json=payload,
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
    speed = configuration["speed"]
    runner.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            raw,
            "-af",
            f"atempo={speed},highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=7",
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
        "words": [{**w, "start": w["start"] / speed, "end": w["end"] / speed} for w in words],
        "configuration": configuration,
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
