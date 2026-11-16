"""Actual known-transcript alignment via stable-ts / Whisper cross-attention DTW."""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("DO_NOT_TRACK", "1")
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--device", default="cpu")
args = parser.parse_args()
if not Path(args.model).is_file():
    raise SystemExit("Local verified Whisper weights required")
import torch
import stable_whisper

torch.set_num_threads(min(4, os.cpu_count() or 1))
request = json.loads(Path(args.input).read_text())
model = stable_whisper.load_model(args.model, device=args.device)
result = model.align(
    request["audio"],
    request["text"],
    language="zh" if request["language"] == "zh-CN" else "en",
    verbose=False,
    regroup=False,
)
if result is None:
    raise RuntimeError("Forced alignment failed")
raw = [
    {"text": w.word, "start": float(w.start), "end": float(w.end)}
    for w in result.all_words()
]
# DTW may assign the same boundary to several Chinese tokens. Preserve every
# token by joining these to the next measured span, never inventing durations.
words = []
pending = ""
for word in raw:
    if word["end"] <= word["start"]:
        pending += word["text"]
        continue
    words.append({**word, "text": pending + word["text"]})
    pending = ""
if pending:
    if not words:
        raise RuntimeError("No measurable alignment spans")
    words[-1]["text"] += pending
Path(args.output).write_text(
    json.dumps(
        {
            "method": "stable-ts-known-transcript-dtw",
            "words": words,
            "raw_tokens": raw,
            "zero_duration_policy": "merge-text-into-adjacent-measured-span",
        },
        ensure_ascii=False,
    )
)
