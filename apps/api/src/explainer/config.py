from functools import lru_cache
from pathlib import Path
import json
import os
import secrets
import tempfile

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXPLAINER_", env_file=".env", extra="ignore")
    data_dir: Path = ROOT / ".data"
    database_url: str = ""
    storage_backend: str = "local"
    s3_endpoint: str = ""
    s3_bucket: str = "explainer"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    alignment_engine: str = "estimated"
    alignment_python: str = ""
    alignment_model: str = ""
    alignment_device: str = "cpu"
    alignment_timeout: int = 300
    dependency_network: str = "none"
    git_allowed_hosts: str = "github.com,gitlab.com"
    engineering_render_image: str = "explainer-engineering-render:3.0.0"
    engineering_max_steps: int = Field(18, ge=5, le=40)
    engineering_tool_timeout: int = Field(900, ge=30, le=7200)
    native_agent_providers: str = ""
    codex_api_key: str = ""
    claude_api_key: str = ""
    claude_base_url: str = ""
    codex_agent_image: str = "explainer-native-codex:3.0.0"
    claude_agent_image: str = "explainer-native-claude:3.0.0"
    native_agent_network: str = "bridge"
    native_agent_runtime: str = "runsc"
    native_agent_timeout: int = Field(600, ge=30, le=1800)
    native_agent_max_turns: int = Field(16, ge=1, le=40)
    native_agent_budget_usd: float = Field(2.0, gt=0, le=20)
    native_agent_repairs: int = Field(1, ge=0, le=2)
    codex_agent_model: str = Field("", max_length=100)
    claude_agent_model: str = Field("", max_length=100)
    api_token: str = ""
    tenant_keys: str = "{}"
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    )
    cookie_secure: bool = False
    max_upload_bytes: int = 25 * 1024 * 1024
    max_expanded_bytes: int = 100 * 1024 * 1024
    max_files: int = 5000
    model_url: str = ""
    model_name: str = ""
    model_key: str = ""
    allow_external_model: bool = False
    image_service_url: str = ""
    image_service_key: str = ""
    image_service_model: str = ""
    image_service_revision: str = "1"
    image_service_timeout: int = Field(180, ge=5, le=600)
    local_material_dir: Path | None = None
    tts_engine: str = "auto"
    tts_url: str = "http://127.0.0.1:7861"
    tts_key: str = ""
    tts_revision: str = "1"
    tts_proxy: str = ""
    edge_voice: str = "zh-CN-YunxiNeural"
    ming_url: str = ""
    ming_key: str = ""
    ming_model: str = "inclusionAI/Ming-3.0-tts-0.5b"
    ming_ref_audio: str = ""
    ming_ref_text: str = ""
    ming_seed: int = 123
    chrome_executable: str = ""
    render_concurrency: int = Field(2, ge=1, le=8)
    render_timeout: int = 1200
    worker_poll_seconds: float = 1.0
    lease_seconds: int = 90
    scheduler: str = "local"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_queue: str = "explainer"
    enable_sandbox: bool = False
    sandbox_image: str = "explainer-sandbox:1.0.0"
    sandbox_runtime: str = "runsc"
    sandbox_timeout: int = 90
    max_active_jobs: int = 3

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_token:
            path = self.data_dir / "access-token"
            if not path.exists():
                # Publish only complete bytes, and never overwrite a concurrent starter's key.
                fd, temporary = tempfile.mkstemp(prefix="access-token-", dir=self.data_dir)
                try:
                    with os.fdopen(fd, "w") as out:
                        out.write(secrets.token_urlsafe(32))
                        out.flush()
                        os.fsync(out.fileno())
                    try:
                        os.link(temporary, path)
                    except FileExistsError:
                        pass
                finally:
                    Path(temporary).unlink(missing_ok=True)
            self.api_token = path.read_text().strip()
        if len(self.api_token) < 24:
            raise ValueError("EXPLAINER_API_TOKEN must have at least 24 characters")
        if set(filter(None, self.native_agent_providers.split(","))) - {"codex", "claude-code"}:
            raise ValueError("Unknown native_agent_providers")
        if self.native_agent_network in {"host", "container", "none"} or self.native_agent_network.startswith(
            "container:"
        ):
            raise ValueError(
                "Native Agents require a dedicated network with model access; host/container networking is forbidden"
            )
        if self.scheduler not in {"local", "temporal"}:
            raise ValueError("scheduler must be local or temporal")
        if self.tts_engine not in {"auto", "espeak", "qwen", "edge", "ming", "none"}:
            raise ValueError("tts_engine must be auto/espeak/qwen/edge/ming/none")
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("storage_backend must be local/s3")
        if self.database_url and not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Only PostgreSQL URLs are supported")
        if self.alignment_engine not in {"estimated", "stable-ts"}:
            raise ValueError("alignment_engine must be estimated/stable-ts")
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("s3_bucket is required")
        if self.local_material_dir is not None:
            if not self.local_material_dir.is_absolute():
                raise ValueError("EXPLAINER_LOCAL_MATERIAL_DIR must be an absolute directory outside the repository")
            self.local_material_dir = self.local_material_dir.resolve()
            if self.local_material_dir.is_relative_to(ROOT.resolve()):
                raise ValueError("EXPLAINER_LOCAL_MATERIAL_DIR must be outside the repository")
        keys = json.loads(self.tenant_keys)
        if not isinstance(keys, dict) or any(
            k == "local"
            or not k.replace("_", "").replace("-", "").isalnum()
            or not isinstance(v, str)
            or len(v) < 24
            for k, v in keys.items()
        ):
            raise ValueError("tenant_keys must map safe tenant IDs to long access keys")
        if len(set([self.api_token, *keys.values()])) != len(keys) + 1:
            raise ValueError("Access keys must be unique per tenant")
        if self.local_material_dir is not None:
            from .local_materials import validate_tenant

            tenants = ["local", *keys]
            for name in tenants:
                validate_tenant(name)
            if len({name.casefold() for name in tenants}) != len(tenants):
                raise ValueError("Local material tenant directories must have distinct names")
        return self

    def keys(self):
        return {"local": self.api_token, **json.loads(self.tenant_keys)}


@lru_cache
def get_settings():
    return Settings().prepare()
