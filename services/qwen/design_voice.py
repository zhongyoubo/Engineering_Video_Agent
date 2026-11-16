"""Create a synthetic professional reference voice once, using downloaded VoiceDesign weights."""

import argparse
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--device", default="cpu")
args = parser.parse_args()

import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

try:
    import onnxruntime

    onnxruntime.disable_telemetry_events()
except ImportError:
    pass
torch.manual_seed(20261028)
model = Qwen3TTSModel.from_pretrained(
    args.model,
    device_map=args.device,
    dtype=torch.bfloat16,
    attn_implementation="sdpa",
    local_files_only=True,
)
text = "我们将从问题出发，逐步理解核心机制，结合实际示例说明工作流程，让复杂的内容清晰易懂。"
style = "标准普通话，成熟稳重的中低男声。正式企业讲解与专业播报风格，清晰通透，语速紧凑自然，逻辑重音准确，句尾干净，录音棚干声。"
wavs, sr = model.generate_voice_design(
    text=text,
    language="Chinese",
    instruct=style,
    non_streaming_mode=True,
    temperature=0.65,
    top_p=0.9,
    max_new_tokens=1200,
)
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
sf.write(out / "reference.wav", wavs[0], sr)
(out / "reference.txt").write_text(text)
print(out)
