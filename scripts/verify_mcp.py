"""Real SDK/stdin/HTTP smoke check. Does not invoke a model, TTS or renderer.

Run with a Python containing the optional MCP SDK. --api-python can select the locked backend env.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def verify(port, env):
    env = {
        **env,
        "EXPLAINER_MCP_URL": f"http://127.0.0.1:{port}",
        "EXPLAINER_MCP_TOKEN": env["EXPLAINER_API_TOKEN"],
    }
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "explainer.mcp_server"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [tool.name for tool in (await session.list_tools()).tools]
            assert len(tools) == 7

            async def call(name, arguments):
                result = await session.call_tool(name, arguments)
                assert not result.isError, result
                return result.structuredContent or json.loads(result.content[0].text)

            capabilities = await call("video_get_capabilities", {})
            assert "native_agents" in capabilities
            project = await call("video_create_project", {"name": "MCP smoke"})
            job_args = {
                "project_id": project["id"],
                "brief": {"title": "MCP", "prompt": "Test", "mode": "storyboard"},
                "idempotency_key": "mcp-smoke-" + str(time.time_ns()),
            }
            job = await call("video_create_job", job_args)
            assert await call("video_create_job", job_args) == job
            observed = await call("video_get_job", {"job_id": job["job_id"]})
            assert observed["state"] == "QUEUED"
            revision = await call(
                "video_get_artifacts", {"revision_id": job["revision_id"]}
            )
            assert revision["project_id"] == project["id"]
            canceled = await call("video_cancel_job", {"job_id": job["job_id"]})
            assert canceled["state"] == "CANCELED"
            fork = await call(
                "video_fork_revision",
                {
                    "revision_id": revision["id"],
                    "expected_version": revision["version"],
                    "auto_render": False,
                },
            )
            assert fork["revision_id"] != revision["id"]
            assert (await call("video_cancel_job", {"job_id": fork["job_id"]}))[
                "state"
            ] == "CANCELED"
            return {
                "initialize": "passed",
                "tool_discovery": tools,
                "http_authenticated_calls": "passed",
                "create_read_cancel": "passed",
                "idempotency_and_revision_fork": "passed",
                "actual_native_inference": False,
            }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-python", default=sys.executable)
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    output = ROOT / ".verify-mcp-v4"
    output.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "apps/api/src"),
        "EXPLAINER_DATA_DIR": str(output / "data"),
        "EXPLAINER_API_TOKEN": "mcp-smoke-not-production-token-123456",
        "EXPLAINER_SCHEDULER": "local",
    }
    log = (output / "api.log").open("w")
    process = subprocess.Popen(
        [
            args.api_python,
            "-m",
            "uvicorn",
            "explainer.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=log,
    )
    try:
        deadline = time.monotonic() + 15
        with httpx.Client(trust_env=False) as client:
            while True:
                if process.poll() is not None:
                    raise RuntimeError("API startup failed; inspect smoke log")
                try:
                    if (
                        client.get(
                            f"http://127.0.0.1:{args.port}/api/health"
                        ).status_code
                        == 200
                    ):
                        break
                except httpx.ConnectError:
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("API startup timeout")
                time.sleep(0.2)
        report = asyncio.run(verify(args.port, env))
        (output / "verification.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
