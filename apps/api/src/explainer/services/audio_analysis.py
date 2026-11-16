"""Measurements of actual PCM audio, not a generated decorative waveform."""

from array import array
import math
import sys
import wave


def waveform(path, bins=600):
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2 or source.getnchannels() != 1:
            raise ValueError("Waveform inspection requires mastered mono PCM16 WAV")
        samples = array("h", source.readframes(source.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
        rate = source.getframerate()
    if not samples:
        raise ValueError("Empty narration audio")
    stride = max(1, math.ceil(len(samples) / bins))
    peaks = [
        round(max(abs(s) for s in samples[i : i + stride]) / 32768, 5) for i in range(0, len(samples), stride)
    ]
    peak = max(abs(s) for s in samples) / 32768
    rms = math.sqrt(sum((s / 32768) ** 2 for s in samples) / len(samples))
    return {
        "duration": len(samples) / rate,
        "sample_rate": rate,
        "peaks": peaks,
        "peak_dbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
        "rms_dbfs": round(20 * math.log10(max(rms, 1e-9)), 2),
        "silent": peak < 0.001,
        "measurement": "PCM amplitude; not LUFS, true peak, pronunciation or listening certification",
    }
