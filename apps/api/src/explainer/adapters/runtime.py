import json
import shutil
import subprocess

from ..db import uid
from ..services.process import ProcessError
from .project_plan import project_plan


def execute_runtime(settings, manifest, brief, directory, runner):
    if brief.runtime == "none":
        return {"state": "not_requested", "message": "未请求真实运行。"}
    if not settings.enable_sandbox or not shutil.which("docker"):
        return {"state": "unavailable", "message": "隔离运行未启用或 Docker 不可用；没有执行用户源码。"}
    try:
        plan = project_plan(manifest, brief)
    except (ValueError, KeyError, TypeError):
        return {"state": "unavailable", "message": "项目入口或声明式演示配置不合法，请检查能力报告。"}
    source, output = directory / "source", directory / "capture"
    source.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    plan_file = directory / "runtime-plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False))
    for name, item in manifest["files"].items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["text"])
    name = uid("explainer")
    args = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "128",
        "--memory",
        "1g",
        "--cpus",
        "2",
        "--user",
        "0:0",
        "--shm-size",
        "128m",
        "--tmpfs",
        "/tmp:rw,nosuid,size=128m",
        "--mount",
        f"type=bind,src={source.resolve()},dst=/source,readonly",
        "--mount",
        f"type=bind,src={output.resolve()},dst=/output",
        "--mount",
        f"type=bind,src={plan_file.resolve()},dst=/plan.json,readonly",
    ]
    if settings.sandbox_runtime:
        args += ["--runtime", settings.sandbox_runtime]
    args += [
        settings.sandbox_image,
        "node",
        "/runner/project-runner.mjs",
        "--plan",
        "/plan.json",
        "--source",
        "/source",
        "--output",
        "/output",
    ]
    try:
        text = runner.run(args, timeout=settings.sandbox_timeout)
        result_file = output / "result.json"
        result = json.loads(result_file.read_text()) if result_file.exists() else {}
        if not result or result.get("schema_version") != "1.0" or result.get("exit_code") != 0:
            return {"state": "failed", "message": "隔离运行退出码不为零。", "log": text[-2000:]}
        if plan["kind"] in {"static-web", "node-web"} and not (output / "page.png").is_file():
            raise ValueError("Capture missing")
        return {
            "state": "observed",
            "message": "仅在本次隔离环境观察到的结果。",
            "result": result,
            "image_path": str(output / "page.png") if plan["kind"] in {"static-web", "node-web"} else None,
            "video_path": str(output / "capture.webm") if (output / "capture.webm").is_file() else None,
            "log": result.get("stdout", text)[-2000:],
            "plan": plan,
        }
    except (ProcessError, ValueError, OSError) as exc:
        return {"state": "failed", "message": "运行或捕获失败；未认定真实演示成功。", "log": str(exc)[-1500:]}
    finally:
        # Killing the CLI alone does not stop a container. Explicit cleanup is mandatory.
        try:
            subprocess.run(
                ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
