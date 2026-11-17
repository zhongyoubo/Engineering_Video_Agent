"""Native CLI agents run in disposable, administrator-provisioned containers only."""

import json
import os
from pathlib import PurePosixPath
import shutil
import subprocess

from ..db import uid
from ..content_taxonomy import planning_guidance
from ..services.process import ProcessError
from .native_contract import strict_schema, validate_design


class NativeAgentError(RuntimeError):
    pass


class NativeOutputError(ValueError):
    """Trusted platform feedback, safe to return to the isolated planning call."""


def capability(settings, provider):
    enabled = provider in settings.native_agent_providers.split(",")
    credential = bool(settings.codex_api_key if provider == "codex" else settings.claude_api_key)
    return {
        "provider": provider,
        "enabled": enabled,
        "credential_configured": credential,
        "docker_available": bool(shutil.which("docker")),
        "transport": "isolated-cli",
        "ready": enabled and credential and bool(shutil.which("docker")),
    }


def safe_source(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError("Unsafe source path")
    blocked = {".git", ".claude", ".codex", ".mcp.json", ".env", "AGENTS.md", "CLAUDE.md"}
    return not any(p in blocked or p.startswith(".env.") for p in path.parts)


def native_plan(
    content,
    brief,
    settings,
    manifest,
    directory,
    runner,
    emit,
    existing_board=None,
    engineering_contract=None,
    validate_result=None,
):
    provider = brief.agent_engine
    if not capability(settings, provider)["ready"]:
        raise NativeAgentError(
            "原生 Agent 未就绪：请配置专用 Worker、容器镜像与对应 API 凭据；没有回退到模板。"
        )
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "source"
    source.mkdir(exist_ok=True)
    for name, item in (manifest or {}).get("files", {}).items():
        if safe_source(name):
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["text"])
    schema = engineering_contract["schema"] if engineering_contract else strict_schema()
    (directory / "schema.json").write_text(json.dumps(schema))
    request = {
        "protocol": "1.0",
        "provider": provider,
        "brief": brief.model_dump(),
        "content": content.model_dump(),
        "content_guidance": planning_guidance(brief),
        "model": settings.codex_agent_model if provider == "codex" else settings.claude_agent_model,
        "budget_usd": settings.native_agent_budget_usd,
        "max_turns": settings.native_agent_max_turns,
        "timeout": settings.native_agent_timeout,
    }
    if engineering_contract:
        request["task"] = "engineering"
        request["payload"] = engineering_contract["payload"]
        request["images"] = []
        for i, frame in enumerate(engineering_contract.get("frames", [])):
            if frame.suffix != ".png" or frame.stat().st_size > 20 * 1024 * 1024:
                raise NativeAgentError("Invalid review frame")
            destination = directory / "frames" / f"{i:03}.png"
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(frame, destination)
            request["images"].append("/input/frames/" + destination.name)
    if brief.agent_change and not engineering_contract:
        if not existing_board:
            raise NativeAgentError("Native edit requires an existing storyboard")
        target = next((s for s in existing_board.scenes if s.id == brief.agent_change.scene_id), None)
        if not target or target.locked:
            raise NativeAgentError("Cannot edit a missing or locked scene")
        request["edit"] = {
            "instruction": brief.agent_change.instruction,
            "target": target.model_dump(exclude={"audio_id", "media_id", "cues"}),
            "context": [{"id": s.id, "title": s.title} for s in existing_board.scenes],
        }
    last_error = None
    for attempt in range(settings.native_agent_repairs + 1):
        runner.guard()
        request["repair"] = ""
        if attempt:
            request["repair"] = (
                "The previous output failed platform validation. Follow the schema and evidence IDs exactly. "
                + (str(last_error) if isinstance(last_error, NativeOutputError) else "")
            )
        (directory / "request.json").write_text(json.dumps(request, ensure_ascii=False))
        name = uid("native")
        image = settings.codex_agent_image if provider == "codex" else settings.claude_agent_image
        key_name = "CODEX_API_KEY" if provider == "codex" else "ANTHROPIC_API_KEY"
        # Docker inherits only this explicitly named key. No tenant/model/storage secrets.
        environment = {
            k: v
            for k, v in os.environ.items()
            if k in {"PATH", "DOCKER_HOST", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH", "HOME"}
        }
        environment[key_name] = settings.codex_api_key if provider == "codex" else settings.claude_api_key
        if provider == "claude-code" and settings.claude_base_url:
            # Administrator-configured Anthropic-compatible endpoint; not a tenant secret.
            # Gateways in bearer mode require AUTH_TOKEN; the pinned CLI ignores
            # non-sk-ant values in ANTHROPIC_API_KEY, so pass both forms.
            environment["ANTHROPIC_BASE_URL"] = settings.claude_base_url
            environment["ANTHROPIC_AUTH_TOKEN"] = settings.claude_api_key
        args = [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--init",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "192",
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--user",
            "10001:10001",
            "--network",
            settings.native_agent_network,
            "--tmpfs",
            "/workspace:rw,nosuid,size=768m,uid=10001,gid=10001",
            "--tmpfs",
            "/home/agent:rw,nosuid,size=256m,uid=10001,gid=10001",
            "--tmpfs",
            "/tmp:rw,nosuid,size=128m,uid=10001,gid=10001",
            "--mount",
            f"type=bind,src={directory.resolve()},dst=/input,readonly",
            "--env",
            key_name,
        ]
        if "ANTHROPIC_BASE_URL" in environment:
            args += ["--env", "ANTHROPIC_BASE_URL"]
        if "ANTHROPIC_AUTH_TOKEN" in environment:
            args += ["--env", "ANTHROPIC_AUTH_TOKEN"]
        if settings.native_agent_runtime:
            args += ["--runtime", settings.native_agent_runtime]
        args += [image]
        events, final = [], []

        def receive(line):
            if len(line) > 400_000:
                raise NativeAgentError("Agent output exceeds limit")
            try:
                message = json.loads(line)
            except ValueError:
                return
            if message.get("protocol") != "1.0":
                return
            if message.get("type") == "result":
                final.append(message)
            elif message.get("type") in {"started", "progress", "completed", "failed"}:
                # Do not store chain-of-thought, raw tool arguments, or credentials.
                event = {
                    "provider": provider,
                    "attempt": attempt + 1,
                    "status": message["type"],
                    "step": str(message.get("step", ""))[:60],
                }
                events.append(event)
                emit("agent.progress", event)

        emit("agent.started", {"provider": provider, "attempt": attempt + 1})
        try:
            runner.run(args, env=environment, timeout=settings.native_agent_timeout + 15, on_line=receive)
            if len(final) != 1 or final[0].get("ok") is not True:
                raise NativeAgentError("Native CLI did not return a successful structured result")
            if engineering_contract:
                value = final[0].get("design")
                if validate_result:
                    value = validate_result(value)
                return value, {
                    "provider": provider,
                    "attempts": attempt + 1,
                    "transport": "isolated-native-cli",
                }
            board = validate_design(final[0].get("design"), content, brief)
            if brief.agent_change:
                from .native_contract import merge_scene_design

                board = merge_scene_design(existing_board, board, brief.agent_change.scene_id)
            emit(
                "agent.completed", {"provider": provider, "attempt": attempt + 1, "scenes": len(board.scenes)}
            )
            report = {
                "protocol": "1.0",
                "provider": provider,
                "transport": "isolated-cli",
                "attempts": attempt + 1,
                "state": "validated",
                "events": events,
                "execution_claim": "Agent output validated; source execution is a separate stage",
            }
            return board, report
        except (ProcessError, ValueError, NativeAgentError) as exc:
            last_error = exc
            emit(
                "agent.failed",
                {
                    "provider": provider,
                    "attempt": attempt + 1,
                    "reason": "CLI execution or structured output validation failed",
                },
            )
        finally:
            subprocess.run(
                ["docker", "rm", "-f", name],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
            )
    # Worker exception logging must not print chained validation inputs or CLI output.
    raise NativeAgentError("原生 Agent 执行或产物校验失败，修复次数已用尽；没有回退到模板。") from None
