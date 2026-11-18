from pathlib import Path
import math, struct, wave

out = Path(__file__).resolve().parents[1] / "assets/sfx"
out.mkdir(exist_ok=True)
for name, frequencies, duration in [
    ("connect", [620, 930], 0.32),
    ("click", [1800], 0.09),
    ("notify", [523.25, 659.25, 783.99], 0.45),
]:
    rate = 48000
    samples = []
    for n in range(round(rate * duration)):
        t = n / rate
        env = min(1, t / 0.008) * math.exp(-t / (duration * 0.32))
        v = (
            sum(math.sin(2 * math.pi * f * t) for f in frequencies)
            / len(frequencies)
            * env
            * 0.4
        )
        samples.append(struct.pack("<h", round(v * 32767)))
    with wave.open(str(out / (name + ".wav")), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(samples))
(out / "README.md").write_text(
    """# Original interaction cues\n\nconnect.wav, click.wav and notify.wav are deterministic, original additive-synthesis Foley authored for this project (48kHz mono PCM). No third-party recording or model voice. Same Apache-2.0 licence as the project. These stylize interactions; they are not physical HDMI signal sounds or hardware measurements. Play quietly under narration; export preserves narration.wav as speech-only. Generator: scripts/generate_interaction_sfx.py.\n"""
)
