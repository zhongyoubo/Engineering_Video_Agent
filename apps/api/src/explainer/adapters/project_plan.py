import json
from pathlib import PurePosixPath
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    target: str = Field(default="", max_length=500)
    value: str = Field(default="", max_length=3000)
    timeout_ms: int = Field(default=10000, ge=100, le=30000)

    @model_validator(mode="after")
    def allowed(self):
        if self.kind not in {
            "click",
            "fill",
            "press",
            "select",
            "assert_visible",
            "assert_text",
            "assert_width_increased",
            "wait_visible",
        }:
            raise ValueError("Unsupported declarative action")
        if not self.target:
            raise ValueError("Target required")
        return self


class RequestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: str = "GET"
    path: str = "/openapi.json"
    body: dict | None = None
    expected_status: int = Field(default=200, ge=100, le=599)

    @model_validator(mode="after")
    def local_only(self):
        if (
            self.method not in {"GET", "POST"}
            or not self.path.startswith("/")
            or self.path.startswith("//")
            or "://" in self.path
            or "\\" in self.path
        ):
            raise ValueError("Only relative local API paths are allowed")
        if len(json.dumps(self.body)) > 20000:
            raise ValueError("Request body too large")
        return self


def safe_relative(value):
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "\\" in value or any(":" in x for x in p.parts):
        raise ValueError("Unsafe project entry")
    return str(p)


def project_plan(manifest, brief):
    files = manifest["files"]
    kind = brief.runtime
    entry = safe_relative(brief.runtime_entry) if brief.runtime_entry else ""
    candidates = sorted(files, key=lambda x: (len(PurePosixPath(x).parts), x))
    config = {}
    config_path = next((p for p in candidates if PurePosixPath(p).name == "explainer.json"), None)
    if config_path:
        config = json.loads(files[config_path]["text"])
        if set(config) - {"entry", "kind", "actions", "requests"}:
            raise ValueError("Unsupported explainer.json fields")
    if kind == "auto":
        entry = entry or config.get("entry", "")
        kind = config.get("kind", "auto")
        if kind == "auto":
            package = next((p for p in candidates if p.endswith("package.json")), None)
            api = next(
                (
                    p
                    for p in candidates
                    if p.endswith(".py") and ("FastAPI(" in files[p]["text"] or "Flask(" in files[p]["text"])
                ),
                None,
            )
            html = next((p for p in candidates if p.endswith("index.html")), None)
            python = next(
                (p for p in candidates if p.endswith(".py") and "__main__" in files[p]["text"]), None
            )
            if package:
                kind = "node-web"
                entry = entry or package
            elif api:
                kind = "python-api"
                entry = entry or api
            elif html:
                kind = "static-web"
                entry = entry or html
            elif python:
                kind = "python-cli"
                entry = entry or python
            else:
                raise ValueError("未识别可运行入口；请声明入口，静态讲解仍可使用")
    entry = safe_relative(entry)
    if entry not in files:
        raise ValueError("入口不在源码快照中")
    root = str(PurePosixPath(entry).parent)
    dependencies = []
    start = []
    build = []
    framework = ""
    if kind == "node-web":
        if not entry.endswith("package.json"):
            raise ValueError("Node Web entry must be package.json")
        package = json.loads(files[entry]["text"])
        scripts = package.get("scripts", {})
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        framework = "vite" if "vite" in deps else "next" if "next" in deps else "node"
        lock = (root + "/" if root != "." else "") + "package-lock.json"
        dependencies = [
            "npm",
            "ci" if lock in files else "install",
            "--offline",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--cache",
            "/tmp/npm-cache",
        ]
        if "build" in scripts:
            build = ["npm", "run", "build"]
        if "dev" in scripts:
            start = ["npm", "run", "dev"]
            if framework == "vite":
                start += ["--", "--host", "127.0.0.1", "--port", "8765", "--strictPort"]
            elif framework == "next":
                start += ["--", "--hostname", "127.0.0.1", "--port", "8765"]
        elif "start" in scripts:
            start = ["npm", "run", "start"]
        else:
            raise ValueError("package.json has no dev/start script")
    elif kind == "python-api":
        if not entry.endswith(".py"):
            raise ValueError("Python API entry must be a Python module")
        module = entry[:-3].replace("/", ".")
        root = "."
        start = [
            "/opt/python/bin/python",
            "-m",
            "uvicorn",
            module + ":app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ]
    elif kind == "python-cli":
        start = ["/opt/python/bin/python", PurePosixPath(entry).name]
    elif kind == "node-cli":
        start = ["node", PurePosixPath(entry).name]
    elif kind != "static-web":
        raise ValueError("Unsupported runtime kind")
    actions = [
        Action.model_validate(a).model_dump() for a in (brief.runtime_actions or config.get("actions", []))
    ]
    requests = [
        RequestSpec.model_validate(a).model_dump() for a in (brief.api_requests or config.get("requests", []))
    ]
    if kind == "python-api" and not requests:
        requests = [RequestSpec().model_dump()]
    return {
        "schema_version": "1.0",
        "kind": kind,
        "entry": entry,
        "working_directory": root,
        "framework": framework,
        "install": dependencies,
        "build": build,
        "start": start,
        "port": 8765,
        "actions": actions,
        "requests": requests,
    }
