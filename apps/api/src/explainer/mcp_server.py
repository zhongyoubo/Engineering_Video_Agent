"""Optional stdio MCP entry point. Tools reuse the authenticated HTTP API and jobs.

Run in a separate environment: pip install -e 'apps/api[mcp]'; python -m explainer.mcp_server.
No user code or provider credentials are executed by this server.
"""

import os
from urllib.parse import urlparse
import httpx


class VideoAPI:
    def __init__(self, url, token, transport=None):
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Configure an HTTP(S) API URL without embedded credentials")
        if not token:
            raise ValueError("EXPLAINER_MCP_TOKEN is required")
        self.client = httpx.Client(
            base_url=url.rstrip("/"),
            headers={"Authorization": "Bearer " + token},
            timeout=30,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def request(self, method, path, body=None, idempotency_key=None):
        if idempotency_key is not None and not 1 <= len(idempotency_key) <= 100:
            raise ValueError("Invalid idempotency key")
        response = self.client.request(
            method, path, json=body, headers={"Idempotency-Key": idempotency_key} if idempotency_key else None
        )
        if response.is_error:
            # Never include request headers or upstream exception strings containing secrets.
            raise ValueError(f"Video API returned HTTP {response.status_code}")
        return response.json()


def create_server(api):
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("engineering-video-agent")

    @server.tool()
    def video_get_capabilities() -> dict:
        """Read configured capabilities; a configured service is not quality certification."""
        return api.request("GET", "/api/v1/capabilities")

    @server.tool()
    def video_create_project(name: str) -> dict:
        """Create a project owned by the API token's tenant."""
        return api.request("POST", "/api/v1/projects", {"name": name})

    @server.tool()
    def video_create_job(project_id: str, brief: dict, idempotency_key: str | None = None) -> dict:
        """Start engineering production; returns job_id, not a fabricated completed video.

        brief accepts title, prompt, input_id, render_profile, voice_spec, mode and other API fields.
        Use mode=storyboard for planning; automatic for the complete production pipeline.
        """
        return api.request(
            "POST", "/api/v3/videos", {"project_id": project_id, "brief": brief}, idempotency_key
        )

    @server.tool()
    def video_get_job(job_id: str) -> dict:
        """Read actual persisted job state and progress."""
        return api.request("GET", "/api/v1/jobs/" + safe_id(job_id))

    @server.tool()
    def video_get_artifacts(revision_id: str) -> dict:
        """Read the revision and tenant-scoped artifact IDs; downloads use the authenticated asset API."""
        return api.request("GET", "/api/v1/revisions/" + safe_id(revision_id))

    @server.tool()
    def video_cancel_job(job_id: str) -> dict:
        """Request cancellation; RUNNING work may return CANCEL_REQUESTED before cleanup."""
        return api.request("POST", "/api/v1/jobs/" + safe_id(job_id) + "/cancel")

    @server.tool()
    def video_fork_revision(
        revision_id: str,
        expected_version: int,
        storyboard: dict | None = None,
        brief: dict | None = None,
        auto_render: bool = True,
    ) -> dict:
        """Save edits as a new revision and optionally produce it. Old artifacts remain versioned."""
        return api.request(
            "POST",
            "/api/v1/revisions/" + safe_id(revision_id) + "/fork",
            {
                "expected_version": expected_version,
                "storyboard": storyboard,
                "brief": brief,
                "auto_render": auto_render,
            },
        )

    return server


def safe_id(value):
    if not value or len(value) > 100 or any(not (c.isascii() and (c.isalnum() or c in "_-")) for c in value):
        raise ValueError("Invalid resource ID")
    return value


def main():
    api = VideoAPI(
        os.getenv("EXPLAINER_MCP_URL", "http://127.0.0.1:8000"), os.getenv("EXPLAINER_MCP_TOKEN", "")
    )
    try:
        create_server(api).run(transport="stdio")
    finally:
        api.client.close()


if __name__ == "__main__":
    main()
