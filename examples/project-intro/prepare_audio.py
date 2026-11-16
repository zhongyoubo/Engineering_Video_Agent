"""Generate actual Mandarin narration for the fixed project-introduction test.

Run after installing apps/api[edge]. Honors the host's explicitly configured CA
bundle for the managed HTTPS proxy; TLS certificate verification stays enabled.
No native-agent inference or renderer is substituted by this audio preparation.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from explainer.adapters.voice import synthesize, voice_cache_key
    from explainer.adapters.alignment import validate_words
    from explainer.config import Settings
    from explainer.domain import Scene
    from explainer.services.process import Runner
    from explainer.specs import VoiceSpec

    # Only exact excerpts from an already-public, immutable README may leave
    # the machine. No project upload, new source, logs or credentials are sent.
    public_ref = "8973bcade2f342eda2a082024ff73c4904b722e5"
    public_readme = subprocess.check_output(
        ["git", "show", f"{public_ref}:README.md"], cwd=ROOT, text=True
    )
    story = json.loads((ROOT / "examples/project-intro/story.json").read_text())
    if any(item["narration"] not in public_readme for item in story):
        raise ValueError("Narration must be an exact excerpt of the public README")
    print(
        f"Public README excerpts only: {public_ref}, {len(story)} excerpts", flush=True
    )
    ca = os.environ.get("SSL_CERT_FILE")
    if ca and Path(ca).is_file():
        import certifi

        certifi.where = lambda: ca
    output = ROOT / ".verify-project-intro"
    output.mkdir(exist_ok=True)
    directory = output / "voice"
    directory.mkdir(exist_ok=True)
    settings = Settings(tts_proxy=os.environ.get("HTTPS_PROXY", ""))
    spec = VoiceSpec(voice_id="zh-CN-YunxiNeural", revision="project-intro-20261117")
    results = {}
    for item in story:
        scene = Scene(**item, type="flow")
        key = voice_cache_key(scene.narration, "zh-CN", "edge", settings, spec)
        receipt = directory / (scene.id + ".json")
        if receipt.exists():
            previous = json.loads(receipt.read_text())
            if previous.get("cache_key") == key and Path(previous["path"]).is_file():
                results[scene.id] = previous
                continue
        result = synthesize(scene, "zh-CN", "edge", settings, directory, Runner(), spec)
        validate_words(result["words"], scene.narration, result["duration"])
        result["cache_key"] = key
        result["sha256"] = hashlib.sha256(Path(result["path"]).read_bytes()).hexdigest()
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        results[scene.id] = result
        print(
            f"{scene.id}: {result['duration']:.2f}s, {len(result['words'])} measured spans",
            flush=True,
        )
    (output / "audio.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
