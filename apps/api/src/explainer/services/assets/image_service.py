"""Administrator-controlled image gateway. Never executes inside generated-code containers."""

import base64
import hashlib
import json
import time
from urllib.parse import urlsplit
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .raster import MAX_IMAGE_BYTES


class ImageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    png_base64: str = Field(min_length=1, max_length=MAX_IMAGE_BYTES * 4 // 3 + 4)
    request_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_.:-]{1,120}$")


def configured(settings):
    if not settings:
        return False
    url = urlsplit(settings.image_service_url)
    local = url.hostname in {"127.0.0.1", "localhost", "::1"}
    return bool(
        url.hostname
        and not url.username
        and not url.password
        and not url.query
        and not url.fragment
        and (url.scheme == "https" or (url.scheme == "http" and local))
        and settings.image_service_model
        and settings.image_service_key
    )


def identity(settings):
    if not configured(settings):
        raise ValueError("Image service is not configured; no provider substitution was performed")
    return dict(
        model=settings.image_service_model,
        revision=settings.image_service_revision,
        endpoint_sha256=hashlib.sha256(settings.image_service_url.encode()).hexdigest(),
    )


def generate(req, settings, request_key, scope, guard, transport=None):
    identity(settings)
    guard()
    body = dict(
        protocol="eva-image-1",
        model=settings.image_service_model,
        prompt=req.image_prompt,
        purpose=req.purpose,
        size=req.size,
        transparent=req.transparent,
    )
    token = hashlib.sha256((scope + ":" + request_key).encode()).hexdigest()
    headers = {"Authorization": "Bearer " + settings.image_service_key, "Idempotency-Key": token}
    limit = MAX_IMAGE_BYTES * 4 // 3 + 4096
    deadline = time.monotonic() + settings.image_service_timeout
    try:
        with httpx.Client(
            timeout=settings.image_service_timeout, follow_redirects=False, transport=transport
        ) as client:
            with client.stream("POST", settings.image_service_url, json=body, headers=headers) as response:
                if (
                    response.status_code != 200
                    or response.headers.get("content-type", "").split(";")[0] != "application/json"
                ):
                    raise ValueError("Image service rejected the request or returned an invalid response")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    guard()
                    size += len(chunk)
                    if size > limit or time.monotonic() > deadline:
                        raise ValueError("Image service response exceeds budget")
                    chunks.append(chunk)
        result = ImageResponse.model_validate(json.loads(b"".join(chunks)))
        data = base64.b64decode(result.png_base64, validate=True)
    except (httpx.HTTPError, ValidationError, json.JSONDecodeError, UnicodeError) as exc:
        # Provider bodies, credentials and transport URL diagnostics never enter Agent logs.
        raise ValueError("Image service failed; check the configured gateway") from exc
    except ValueError as exc:
        raise ValueError("Image service returned an invalid or oversized PNG response") from exc
    guard()
    return data, result.request_id
