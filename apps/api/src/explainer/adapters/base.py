from typing import Protocol
from pydantic import BaseModel


class AdapterManifest(BaseModel):
    id: str
    version: str = "1.0.0"
    protocol: str = "1.0"
    capabilities: list[str]
    trusted: bool = True


class RuntimeAdapter(Protocol):
    manifest: AdapterManifest

    def execute(self, source_files: dict, entry: str, workdir, runner) -> dict: ...


MANIFESTS = [
    AdapterManifest(
        id="agent.engineering",
        version="3.0.0",
        capabilities=["production-plan", "tsx-authoring", "build-preview-review-repair", "source-export"],
    ),
    AdapterManifest(
        id="render.engineering",
        version="3.0.0",
        capabilities=["isolated-offline", "required-font", "keyframe-audit", "current-source-gates"],
    ),
    AdapterManifest(
        id="agent.codex",
        version="2.1.0",
        capabilities=["native-cli", "source-reading", "structured-design", "isolated-execution"],
    ),
    AdapterManifest(
        id="agent.claude-code",
        version="2.1.0",
        capabilities=["native-cli", "source-reading", "structured-design", "isolated-execution"],
    ),
    AdapterManifest(id="source.static", capabilities=["source.text", "python.ast", "manifest", "evidence"]),
    AdapterManifest(id="planner.template", capabilities=["prompt", "source", "storyboard"]),
    AdapterManifest(id="planner.llm", capabilities=["schema-output", "configured-model-only"]),
    AdapterManifest(id="runtime.docker", capabilities=["static-web", "python-cli", "network-none"]),
    AdapterManifest(id="voice.espeak", capabilities=["local-voice", "zh-CN", "en-US"]),
    AdapterManifest(id="voice.qwen", capabilities=["configured-service", "fixed-reference-voice"]),
    AdapterManifest(id="voice.edge", capabilities=["cloud-service", "zh-CN", "en-US"]),
    AdapterManifest(id="voice.ming", capabilities=["openai-compatible-service", "voice-design", "zh-CN"]),
    AdapterManifest(id="render.remotion", capabilities=["mp4", "1920x1080", "30fps", "editable-ir"]),
]
