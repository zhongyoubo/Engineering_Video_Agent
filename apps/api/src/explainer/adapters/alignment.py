import json
import os
import re
from pathlib import Path

from ..config import ROOT


def validate_words(words, text, duration):
    if not words:
        raise ValueError("Alignment returned no words")
    last = 0.0
    for item in words:
        if not (0 <= item["start"] < item["end"] <= duration + 0.08) or item["start"] < last - 0.02:
            raise ValueError("Non-monotonic or out-of-range alignment")
        if not isinstance(item["text"], str):
            raise ValueError("Invalid aligned text")
        last = item["end"]

    def normalize(s):
        return re.sub(r"[\W_]+", "", s).lower()

    if normalize("".join(w["text"] for w in words)) != normalize(text):
        raise ValueError("Aligned transcript differs from narration")
    return words


def forced_align(path, text, language, duration, settings, directory, runner):
    if not settings.alignment_python or not Path(settings.alignment_model).is_file():
        raise ValueError("Configure alignment_python and local alignment_model weights")
    source = directory / "align-request.json"
    output = directory / "align-result.json"
    source.write_text(
        json.dumps(
            {"audio": str(Path(path).resolve()), "text": text, "language": language}, ensure_ascii=False
        )
    )
    env = os.environ.copy()
    env.update(
        HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1", TOKENIZERS_PARALLELISM="false"
    )
    runner.run(
        [
            settings.alignment_python,
            ROOT / "services/alignment/align.py",
            "--input",
            source,
            "--output",
            output,
            "--model",
            settings.alignment_model,
            "--device",
            settings.alignment_device,
        ],
        timeout=settings.alignment_timeout,
        env=env,
    )
    words = json.loads(output.read_text())["words"]
    return validate_words(words, text, duration)
