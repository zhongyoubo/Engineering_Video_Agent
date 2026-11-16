"""Only launched through offline_run.py; all IP socket creation is denied before imports."""

import io, json, os, sys, base64, traceback
import torch
import soundfile as sf
import onnxruntime

onnxruntime.disable_telemetry_events()
from qwen_tts import Qwen3TTSModel

torch.set_num_threads(int(os.getenv("QWEN_CPU_THREADS", "4")))
model = Qwen3TTSModel.from_pretrained(
    os.environ["QWEN_BASE_MODEL"],
    device_map=os.getenv("QWEN_DEVICE", "cpu"),
    # Consumer CPUs without AVX512-BF16/AMX emulate bfloat16 on a slow path;
    # float32 is several times faster there. Keep bf16 for accelerators.
    dtype=torch.float32 if os.getenv("QWEN_DEVICE", "cpu") == "cpu" else torch.bfloat16,
    attn_implementation="sdpa",
    local_files_only=True,
)
audio, sr = sf.read(os.environ["QWEN_REFERENCE_WAV"], dtype="float32")
with open(os.environ["QWEN_REFERENCE_TEXT"]) as f:
    reference = f.read()
prompt = model.create_voice_clone_prompt(
    ref_audio=(audio, sr), ref_text=reference, x_vector_only_mode=False
)
print("@@READY@@", flush=True)
for line in sys.stdin:
    try:
        body = json.loads(line)
        if len(body["text"]) > 1600:
            raise ValueError("Text too long")
        wavs, sr = model.generate_voice_clone(
            text=body["text"],
            language="Chinese" if body["language"] == "zh-CN" else "English",
            voice_clone_prompt=prompt,
            non_streaming_mode=True,
            max_new_tokens=2800,
            temperature=0.65,
            top_p=0.9,
        )
        result = io.BytesIO()
        sf.write(result, wavs[0], sr, format="WAV", subtype="PCM_16")
        print(
            "@@RESULT@@"
            + json.dumps({"audio": base64.b64encode(result.getvalue()).decode()}),
            flush=True,
        )
    except Exception:
        traceback.print_exc(file=sys.stderr)
        print(
            "@@RESULT@@" + json.dumps({"error": "Local inference failed"}), flush=True
        )
