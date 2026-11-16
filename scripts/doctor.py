import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.config import get_settings
s = get_settings()
print(json.dumps({"python": sys.version.split()[0], "node": shutil.which("node"), "ffmpeg": shutil.which("ffmpeg"),
    "ffprobe": shutil.which("ffprobe"), "espeak": shutil.which("espeak-ng"), "docker": shutil.which("docker"),
    "node_modules": (ROOT/"node_modules").is_dir(), "font": (ROOT/"assets/fonts/NotoSansCJKsc-Regular.otf").exists(),
    "native_agent_providers": s.native_agent_providers, "native_agent_runtime": s.native_agent_runtime, "scheduler": s.scheduler, "model_enabled": s.allow_external_model and bool(s.model_url),
    "sandbox_enabled": s.enable_sandbox, "chrome_configured": bool(s.chrome_executable),
    "access_key_file": str(s.data_dir/"access-token")}, ensure_ascii=False, indent=2))

