"""Generated code executes only in credential-free offline containers."""

import json
from pathlib import Path
import shutil
import subprocess
from ...db import uid
from PIL import Image, ImageStat
import hashlib
from ..process import ProcessError
from .workspace import EngineeringError


def inspect_frame(path):
    with Image.open(path) as image:
        if image.format != "PNG" or image.size != (1920, 1080):
            raise EngineeringError("Preview must be a real 1920x1080 PNG")
        image.load()
        region = image.convert("RGB").crop((0, 0, 1920, 900))
        if max(ImageStat.Stat(region).stddev) < 3:
            raise EngineeringError("Preview is visually empty above the caption area")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RenderTools:
    def __init__(self, settings, runner):
        self.settings, self.runner = settings, runner

    def execute(self, workspace, action):
        if action not in {"build", "preview", "final"}:
            raise EngineeringError("Unknown engineering tool")
        if not shutil.which("docker"):
            raise EngineeringError("工程渲染需要 Docker 隔离环境；未在宿主机执行生成代码。")
        name = uid("engineering")
        output = workspace.root / f"tool-{workspace.state['iteration']:03}-{action}"
        # Fresh output: a previous receipt must never satisfy a new invocation.
        if output.exists():
            shutil.rmtree(output)
        output.mkdir()
        output.chmod(0o777)
        args = [
            "docker",
            "run",
            "--rm",
            "--init",
            "--name",
            name,
            "--read-only",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--memory",
            "3g",
            "--cpus",
            "2",
            "--user",
            "10001:10001",
            "--shm-size",
            "256m",
            "--tmpfs",
            "/work:rw,nosuid,size=768m,uid=10001,gid=10001",
            "--tmpfs",
            "/tmp:rw,nosuid,size=256m,uid=10001,gid=10001",
            "--mount",
            f"type=bind,src={workspace.project.resolve()},dst=/input,readonly",
            "--mount",
            f"type=bind,src={output.resolve()},dst=/output",
        ]
        if self.settings.native_agent_runtime:
            args += ["--runtime", self.settings.native_agent_runtime]
        args += [self.settings.engineering_render_image, action]
        try:
            try:
                self.runner.run(
                    args,
                    timeout=self.settings.engineering_tool_timeout,
                    env={"PATH": __import__("os").environ.get("PATH", "/usr/bin:/bin")},
                )
            except ProcessError:
                if not (output / "result.json").is_file():
                    return {
                        "ok": False,
                        "action": action,
                        "diagnostic": "Container build/render failed without a valid receipt",
                    }
            receipt = output / "result.json"
            if receipt.is_symlink() or receipt.stat().st_size > 20000:
                raise EngineeringError("Invalid tool receipt")
            result = json.loads(receipt.read_text())
            if (
                result.get("protocol") != "3.0"
                or result.get("action") != action
                or not isinstance(result.get("ok"), bool)
            ):
                raise EngineeringError("Invalid tool protocol")
            if result["ok"] and action == "preview":
                frames = result.get("frames", [])
                if not 1 <= len(frames) <= 48:
                    raise EngineeringError("Missing sampled keyframes")
                for frame in frames:
                    p = output / frame["name"]
                    if (
                        Path(frame["name"]).name != frame["name"]
                        or p.is_symlink()
                        or not p.is_file()
                        or p.stat().st_size > 20 * 1024 * 1024
                    ):
                        raise EngineeringError("Invalid review frame")
                hashes = [inspect_frame(output / f["name"]) for f in frames]
                if len(frames) >= 3 and len(set(hashes)) == 1:
                    return {
                        "ok": False,
                        "action": action,
                        "diagnostic": "All sampled frames are identical; no visual progression was observed",
                    }
                result["frame_checks"] = {
                    "dimensions": "passed",
                    "nonempty": "passed",
                    "distinct": len(set(hashes)),
                }
                result["frames"] = [
                    {"name": str((output / f["name"]).relative_to(workspace.root)), "frame": f["frame"]}
                    for f in frames
                ]
            if result["ok"] and action == "final":
                if not (output / "video.mp4").is_file() or (output / "video.mp4").is_symlink():
                    raise EngineeringError("Missing final video")
                result["video"] = str(output / "video.mp4")
            return result
        finally:
            subprocess.run(
                ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20
            )
