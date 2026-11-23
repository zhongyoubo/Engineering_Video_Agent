import asyncio
import hashlib
import json
import io
import shutil
import time
import zipfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adapters.base import MANIFESTS
from .adapters.native_agent import capability as native_capability
from .content_taxonomy import taxonomy_options
from .visual_scene import visual_scene_guidance
from .semantic_scene import semantic_guidance
from .creative_scene import creative_guidance
from .api_materials import register_material_routes
from .services.assets.image_service import configured as image_service_configured
from .config import ROOT, get_settings
from .db import Database, encode, uid
from .domain import CreateProject, CreateVideo, ForkRevision, CreateEngineeringVideo
from .security import identify, owned, tenant
from .services.ingestion import InvalidArchive, read_archive
from .services.materials import material_library
from .storage import Storage


def dependencies(settings=Depends(get_settings)):
    db = Database(settings.data_dir, settings.database_url)
    return settings, db, Storage(settings, db)


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    Database(settings.data_dir, settings.database_url)
    yield


app = FastAPI(
    title="Explainer Studio API",
    version="3.0.0",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)


@app.middleware("http")
async def request_policy(request: Request, call_next):
    settings = get_settings()
    request.state.request_id = uid("req")
    received = 0
    oversized = False
    original_receive = request.receive

    async def limited_receive():
        nonlocal received, oversized
        message = await original_receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > settings.max_upload_bytes + 1024 * 1024:
                oversized = True
                raise HTTPException(413, "请求超过大小限制")
        return message

    request._receive = limited_receive
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins.split(","):
            return JSONResponse(
                {"error": {"code": "ORIGIN_DENIED", "message": "Origin rejected"}}, status_code=403
            )
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > settings.max_upload_bytes + 1024 * 1024):
            return JSONResponse(
                {"error": {"code": "PAYLOAD_TOO_LARGE", "message": "请求超过大小限制"}}, status_code=413
            )
    response = await call_next(request)
    if oversized:
        response = JSONResponse(
            {"error": {"code": "PAYLOAD_TOO_LARGE", "message": "请求超过大小限制"}}, status_code=413
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "HTTP_" + str(exc.status_code),
                "message": str(exc.detail),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic errors may embed raw credential values; only return location and message.
    return JSONResponse(
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "输入不符合协议",
                "details": [{"loc": e["loc"], "message": e["msg"]} for e in exc.errors()],
            }
        },
        status_code=422,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


class Login(BaseModel):
    token: str = Field(max_length=300)


class ChangeInstruction(BaseModel):
    scene_id: str
    instruction: str = Field(min_length=1, max_length=3000)
    auto_render: bool = True


class GitImport(BaseModel):
    url: str = Field(max_length=500)
    ref: str = Field(default="HEAD", max_length=160)


@app.post("/api/v1/projects/{project_id}/git-import", status_code=201)
def import_git(project_id: str, body: GitImport, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    from .services.git_input import git_snapshot

    settings, db, storage = deps
    owned(db, "projects", project_id, tenant_id)
    try:
        data, origin = git_snapshot(body.url, body.ref, settings)
        manifest = read_archive(data, settings)
    except (ValueError, OSError):
        raise HTTPException(422, "Git 地址、版本或归档不符合策略")
    except Exception:
        raise HTTPException(502, "Git 获取未完成；没有执行远程源码")
    manifest["origin"] = origin
    asset = storage.put(tenant_id, data, "source", "git-snapshot.zip", "application/zip")
    identifier = uid("inp")
    db.execute(
        "INSERT INTO inputs VALUES(?,?,?,?,?,?)",
        (identifier, tenant_id, project_id, asset["id"], encode(manifest), time.time()),
    )
    return {"id": identifier, "files_count": len(manifest["files"]), "origin": origin}


@app.post("/api/session")
def login(body: Login, response: Response, settings=Depends(get_settings)):
    t = identify(body.token, settings)
    if not t:
        raise HTTPException(401, "访问密钥不正确")
    response.set_cookie(
        "explainer_session",
        body.token,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        max_age=86400,
        path="/",
    )
    return {"tenant": t}


@app.delete("/api/session")
def logout(response: Response, tenant_id=Depends(tenant)):
    response.delete_cookie("explainer_session", path="/")
    return {"ok": True}


@app.get("/api/session")
def session(tenant_id=Depends(tenant)):
    return {"tenant": tenant_id}


@app.get("/api/v1/capabilities")
def capabilities(tenant_id=Depends(tenant), deps=Depends(dependencies)):
    settings, _, _ = deps
    return {
        "adapters": [m.model_dump() for m in MANIFESTS],
        "material_library": material_library(),
        "content_taxonomy": taxonomy_options(),
        "visual_scene_toolkit": visual_scene_guidance(),
        "semantic_scene_toolkit": semantic_guidance(),
        "creative_production": creative_guidance(),
        "asset_factory": {
            "library_asset": True,
            "component_svg": True,
            "project_image": True,
            "image_service": image_service_configured(settings),
        },
        "model": bool(settings.model_url and settings.model_name and settings.allow_external_model),
        "model_name": settings.model_name if settings.allow_external_model else "local-template",
        "voice": {
            "default": settings.tts_engine,
            "espeak": bool(shutil.which("espeak-ng")),
            "qwen_configured": settings.tts_engine == "qwen",
            "edge": settings.edge_voice,
            "ming_configured": bool(settings.ming_url),
        },
        "runtime": {
            "enabled": settings.enable_sandbox,
            "docker": bool(shutil.which("docker")),
            "adapters": ["auto", "static-web", "python-cli", "node-cli", "node-web", "python-api"],
        },
        "native_agents": [native_capability(settings, p) for p in ["codex", "claude-code"]],
        "video_modes": {
            "default_creation": "engineering",
            "engineering_endpoint": "/api/v3/videos",
            "legacy_endpoint": "/api/v1/videos",
            "resolutions": ["1080p", "4k"],
            "design_packs": ["editorial_warm", "workspace_tech", "neon_horizon"],
            "motion_patterns": ["overview", "code_scan", "compare", "graph", "capacity", "queue", "depth"],
        },
        "scheduler": settings.scheduler,
        "max_upload_bytes": settings.max_upload_bytes,
    }


@app.get("/api/v1/material-library")
def get_material_library(query: str = "", style: str = "", asset_type: str = "", tenant_id=Depends(tenant)):
    from .services.materials import search_materials

    if len(query) > 160 or len(style) > 60 or asset_type not in {"", "component", "image", "model"}:
        raise HTTPException(422, "Invalid material filters")
    return search_materials(query, style, asset_type)


@app.get("/api/v1/material-library/{material_id}/preview")
def material_preview(material_id: str, version: str, tenant_id=Depends(tenant)):
    from .material_packs import resolve_material

    try:
        pack, item, files, stamp = resolve_material(f"library:{material_id}@{version}")
        if not item.preview:
            raise ValueError("No preview")
    except ValueError as exc:
        raise HTTPException(404, "Material preview not found") from exc
    return FileResponse(files[item.preview], media_type="image/png")


@app.get("/api/v1/content-taxonomy")
def get_content_taxonomy(tenant_id=Depends(tenant)):
    return taxonomy_options()


@app.get("/api/v1/projects")
def projects(tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    return {
        "items": db.all("SELECT * FROM projects WHERE tenant=? ORDER BY created DESC LIMIT 100", (tenant_id,))
    }


@app.post("/api/v1/projects", status_code=201)
def create_project(body: CreateProject, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    project_id = uid("prj")
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", (project_id, tenant_id, body.name, time.time()))
    return owned(db, "projects", project_id, tenant_id)


@app.post("/api/v1/projects/{project_id}/inputs", status_code=201)
async def upload(
    project_id: str, file: UploadFile = File(...), tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    settings, db, storage = deps
    owned(db, "projects", project_id, tenant_id)
    chunks, length = [], 0
    while chunk := await file.read(65536):
        length += len(chunk)
        if length > settings.max_upload_bytes:
            raise HTTPException(413, "归档超过大小限制")
        chunks.append(chunk)
    await file.close()
    data = b"".join(chunks)
    try:
        manifest = read_archive(data, settings)
    except InvalidArchive as exc:
        raise HTTPException(422, str(exc)) from exc
    a = storage.put(tenant_id, data, "source", "source.zip", "application/zip")
    input_id = uid("inp")
    db.execute(
        "INSERT INTO inputs VALUES(?,?,?,?,?,?)",
        (input_id, tenant_id, project_id, a["id"], encode(manifest), time.time()),
    )
    return {
        "id": input_id,
        "files_count": len(manifest["files"]),
        "skipped": manifest["skipped"],
        "files": list(manifest["files"])[:200],
        "sha256": manifest["archive_hash"],
    }


@app.get("/api/v1/projects/{project_id}/inputs")
def inputs(project_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    owned(db, "projects", project_id, tenant_id)
    rows = db.all(
        "SELECT id,created,manifest FROM inputs WHERE project_id=? AND tenant=? ORDER BY created DESC",
        (project_id, tenant_id),
    )
    return {
        "items": [
            {"id": r["id"], "created": r["created"], "files_count": len(json.loads(r["manifest"])["files"])}
            for r in rows
        ]
    }


@app.post("/api/v1/projects/{project_id}/import", status_code=202)
async def import_project(
    project_id: str, file: UploadFile = File(...), tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    from .domain import Brief, ContentIR, StoryboardIR

    settings, db, storage = deps
    owned(db, "projects", project_id, tenant_id)
    data = bytearray()
    while chunk := await file.read(65536):
        data.extend(chunk)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(413, "工程包超过大小限制")
    await file.close()
    try:
        read_archive(bytes(data), settings)  # validates every member name, ratio, type and size
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            board = StoryboardIR.model_validate_json(z.read("project.json"))
            content = ContentIR.model_validate_json(z.read("content.json"))
            manifest = json.loads(z.read("manifest.json"))
            mapping = {}
            for old, item in manifest.items():
                blob = z.read(item["path"])
                if hashlib.sha256(blob).hexdigest() != item["sha256"]:
                    raise ValueError("Media checksum mismatch")
                mime = item["mime"]
                if mime not in {"audio/wav", "image/png", "video/webm"}:
                    raise ValueError("Unsupported imported media")
                valid = (
                    mime == "audio/wav"
                    and blob[:4] == b"RIFF"
                    and blob[8:12] == b"WAVE"
                    or mime == "image/png"
                    and blob.startswith(b"\x89PNG\r\n\x1a\n")
                    or mime == "video/webm"
                    and blob.startswith(b"\x1aE\xdf\xa3")
                )
                if not valid:
                    raise ValueError("Media signature mismatch")
                mapping[old] = storage.put(tenant_id, blob, "imported", item["path"].split("/")[-1], mime)[
                    "id"
                ]
            for scene in board.scenes:
                scene.audio_id = mapping[scene.audio_id] if scene.audio_id else None
                scene.media_id = mapping[scene.media_id] if scene.media_id else None
                scene.verification = "concept"  # imported footage cannot establish a new trusted execution
                scene.locked = False
            board.notices.append("导入工程：媒体来自用户文件，不作为本次运行验证。")
    except (InvalidArchive, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        raise HTTPException(422, "工程格式、路径、媒体校验或 Schema 不合法")
    brief = Brief(
        title=board.title,
        prompt="Imported editable project",
        language=board.language,
        accent=board.accent,
        target_seconds=max(20, min(900, round(board.total_frames / 30))),
        mode="storyboard",
    )
    return await schedule(
        settings,
        insert_revision(
            db, settings, tenant_id, project_id, brief, storyboard=board, content=encode(content.model_dump())
        ),
    )


def insert_revision(
    db,
    settings,
    tenant_id,
    project_id,
    brief,
    parent=None,
    storyboard=None,
    content=None,
    idempotency_key=None,
    request_hash=None,
):
    revision_id, job_id, now = uid("rev"), uid("job"), time.time()
    result = {"revision_id": revision_id, "job_id": job_id, "state": "QUEUED"}
    with db.transaction() as c:
        db.lock_tenant(c, tenant_id)
        if idempotency_key:
            old = c.execute(
                "SELECT * FROM idempotency WHERE tenant=? AND key=?", (tenant_id, idempotency_key)
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise HTTPException(409, "Idempotency-Key 已用于不同请求")
                return json.loads(old["response"])
        active = c.execute(
            "SELECT count(*) FROM jobs WHERE tenant=? AND state IN ('QUEUED','RUNNING','CANCEL_REQUESTED')",
            (tenant_id,),
        ).fetchone()[0]
        if active >= settings.max_active_jobs:
            raise HTTPException(429, "并发任务配额已满")
        c.execute(
            "INSERT INTO revisions(id,tenant,project_id,parent_id,brief,content,storyboard,created) VALUES(?,?,?,?,?,?,?,?)",
            (
                revision_id,
                tenant_id,
                project_id,
                parent,
                encode(brief.model_dump()),
                content,
                encode(storyboard.model_dump()) if storyboard else None,
                now,
            ),
        )
        c.execute(
            "INSERT INTO jobs(id,tenant,revision_id,state,created,updated) VALUES(?,?,?,?,?,?)",
            (job_id, tenant_id, revision_id, "QUEUED", now, now),
        )
        if idempotency_key:
            c.execute(
                "INSERT INTO idempotency VALUES(?,?,?,?)",
                (tenant_id, idempotency_key, request_hash, encode(result)),
            )
        db.event({"id": job_id, "tenant": tenant_id}, "job.queued", result, c)
    return result


async def schedule(settings, result):
    if settings.scheduler == "temporal":
        try:
            from .temporal_worker import dispatch

            await dispatch(settings, result["job_id"])
        except Exception as exc:
            # Keep the committed job. A retry with the same key can safely re-dispatch.
            raise HTTPException(503, f"任务已保存，但 Temporal 不可用。任务 ID：{result['job_id']}") from exc
    return result


@app.post("/api/v1/videos", status_code=202)
async def create_video(
    body: CreateVideo,
    idempotency_key: str | None = Header(default=None, max_length=100),
    tenant_id=Depends(tenant),
    deps=Depends(dependencies),
):
    settings, db, _ = deps
    owned(db, "projects", body.project_id, tenant_id)
    if body.brief.agent_change:
        raise HTTPException(422, "场景修改请使用已有版本的 changes 接口")
    if body.brief.input_id:
        value = owned(db, "inputs", body.brief.input_id, tenant_id)
        if value["project_id"] != body.project_id:
            raise HTTPException(422, "输入不属于当前项目")
    request_hash = hashlib.sha256(encode(body.model_dump()).encode()).hexdigest()
    result = insert_revision(
        db,
        settings,
        tenant_id,
        body.project_id,
        body.brief,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    return await schedule(settings, result)


@app.post("/api/v3/videos", status_code=202)
async def create_engineering_video(
    body: CreateEngineeringVideo,
    idempotency_key: str | None = Header(default=None, max_length=100),
    tenant_id=Depends(tenant),
    deps=Depends(dependencies),
):
    return await create_video(CreateVideo.model_validate(body.model_dump()), idempotency_key, tenant_id, deps)


def revision_view(db, row):
    result = dict(row)
    for key in ["brief", "content", "storyboard", "quality"]:
        result[key] = json.loads(result[key]) if result.get(key) else None
    result["outputs"] = {
        o["role"]: o["asset_id"] for o in db.all("SELECT * FROM outputs WHERE revision_id=?", (row["id"],))
    }
    return result


@app.get("/api/v1/revisions/{revision_id}")
def get_revision(revision_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    return revision_view(db, owned(db, "revisions", revision_id, tenant_id))


@app.get("/api/v1/revisions/{revision_id}/compare/{base_id}")
def compare_revisions(revision_id: str, base_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    current = revision_view(db, owned(db, "revisions", revision_id, tenant_id))
    base = revision_view(db, owned(db, "revisions", base_id, tenant_id))
    if current["project_id"] != base["project_id"]:
        raise HTTPException(422, "只能比较同一项目的版本")
    before = {s["id"]: s for s in (base["storyboard"] or {}).get("scenes", [])}
    after = {s["id"]: s for s in (current["storyboard"] or {}).get("scenes", [])}
    changed = []
    for identifier in sorted(before.keys() | after.keys()):
        fields = (
            ["added"]
            if identifier not in before
            else ["removed"]
            if identifier not in after
            else [
                key
                for key in sorted(before[identifier].keys() | after[identifier].keys())
                if before[identifier].get(key) != after[identifier].get(key)
            ]
        )
        if fields:
            changed.append({"id": identifier, "fields": fields})
    return {
        "revision_id": revision_id,
        "base_id": base_id,
        "changed_scenes": changed,
        "settings_changed": [
            key
            for key in sorted(current["brief"].keys() | base["brief"].keys())
            if current["brief"].get(key) != base["brief"].get(key)
        ],
    }


@app.post("/api/v1/revisions/{revision_id}/fork", status_code=202)
async def fork_revision(
    revision_id: str, body: ForkRevision, tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    settings, db, _ = deps
    original = owned(db, "revisions", revision_id, tenant_id)
    if original["version"] != body.expected_version:
        raise HTTPException(409, "版本冲突，请重新加载")
    from .domain import Brief, StoryboardIR

    old_board = StoryboardIR.model_validate_json(original["storyboard"]) if original["storyboard"] else None
    board = body.storyboard or old_board
    brief = body.brief or Brief.model_validate_json(original["brief"])
    old_brief = Brief.model_validate_json(original["brief"])
    if brief.input_id:
        source = owned(db, "inputs", brief.input_id, tenant_id)
        if source["project_id"] != original["project_id"]:
            raise HTTPException(422, "输入不属于当前项目")
    content = original["content"]
    if (
        brief.input_id != old_brief.input_id
        or brief.prompt != old_brief.prompt
        or brief.title != old_brief.title
    ):
        content, board = None, None
    if (
        brief.editorial != old_brief.editorial
        or brief.presentation_profile != old_brief.presentation_profile
        or brief.audience != old_brief.audience
        or brief.language != old_brief.language
        or brief.video_mode != old_brief.video_mode
    ):
        board = None
    if board:
        old = {s.id: s for s in old_board.scenes} if old_board else {}
        for scene in board.scenes:
            prior = old.get(scene.id)
            if not prior or scene.creation != prior.creation:
                scene.compiled_creative_events = []
            if prior and prior.locked and scene.model_dump() != prior.model_dump():
                unlocking_only = not scene.locked and scene.model_dump(
                    exclude={"locked"}
                ) == prior.model_dump(exclude={"locked"})
                if not unlocking_only:
                    raise HTTPException(409, "场景已锁定；请先创建只解除锁定的版本")
            for aid in [scene.audio_id, scene.media_id]:
                if aid:
                    owned(db, "assets", aid, tenant_id)
                    if not prior or aid not in [prior.audio_id, prior.media_id]:
                        raise HTTPException(422, "不能在分镜中注入未引用的素材")
            if (
                not prior
                or scene.narration != prior.narration
                or brief.voice != old_brief.voice
                or brief.voice_spec != old_brief.voice_spec
                or brief.language != old_brief.language
            ):
                scene.audio_id, scene.cues = None, []
                scene.compiled_events = []
                scene.compiled_object_events = []
                scene.compiled_semantic_events = []
                scene.compiled_creative_events = []
    brief.mode = "automatic" if body.auto_render else "storyboard"
    return await schedule(
        settings,
        insert_revision(
            db,
            settings,
            tenant_id,
            original["project_id"],
            brief,
            parent=revision_id,
            storyboard=board,
            content=content,
        ),
    )


@app.get("/api/v1/jobs")
def jobs(tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    return {
        "items": db.all(
            "SELECT jobs.*,revisions.brief FROM jobs JOIN revisions ON revisions.id=jobs.revision_id "
            "WHERE jobs.tenant=? ORDER BY jobs.created DESC LIMIT 100",
            (tenant_id,),
        )
    }


@app.post("/api/v1/revisions/{revision_id}/source", status_code=202)
async def update_source(
    revision_id: str, file: UploadFile = File(...), tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    from .domain import Brief

    original = owned(deps[1], "revisions", revision_id, tenant_id)
    uploaded = await upload(original["project_id"], file, tenant_id, deps)
    brief = Brief.model_validate_json(original["brief"])
    brief.input_id = uploaded["id"]
    # Source evidence changes invalidate scene references. Voice cache reuses identical narration.
    return await schedule(
        deps[0],
        insert_revision(deps[1], deps[0], tenant_id, original["project_id"], brief, parent=revision_id),
    )


@app.post("/api/v1/revisions/{revision_id}/changes", status_code=202)
async def changes(
    revision_id: str, body: ChangeInstruction, tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    from .domain import StoryboardIR, Brief, AgentChange
    from .services.changes import apply_instruction

    settings, db, _ = deps
    original = owned(db, "revisions", revision_id, tenant_id)
    if not original["storyboard"]:
        raise HTTPException(409, "分镜尚未生成")
    brief = Brief.model_validate_json(original["brief"])
    if brief.agent_engine != "pipeline":
        current = StoryboardIR.model_validate_json(original["storyboard"])
        target = next((scene for scene in current.scenes if scene.id == body.scene_id), None)
        if not target or target.locked:
            raise HTTPException(409, "场景不存在或已锁定，请先解锁")
        brief.agent_change = AgentChange(scene_id=body.scene_id, instruction=body.instruction)
        brief.mode = "automatic" if body.auto_render else "storyboard"
        return await schedule(
            settings,
            insert_revision(
                db,
                settings,
                tenant_id,
                original["project_id"],
                brief,
                parent=revision_id,
                storyboard=current,
                content=original["content"],
            ),
        )
    try:
        board = apply_instruction(
            StoryboardIR.model_validate_json(original["storyboard"]),
            body.instruction,
            body.scene_id,
            settings,
        )
    except (ValueError, KeyError, IndexError):
        raise HTTPException(422, "修改未通过校验；请使用“标题改为…”或“旁白改为…”，或直接编辑分镜")
    except Exception:
        raise HTTPException(502, "模型修改未完成，原版本保持不变")
    return await fork_revision(
        revision_id,
        ForkRevision(expected_version=original["version"], storyboard=board, auto_render=body.auto_render),
        tenant_id,
        deps,
    )


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    return owned(db, "jobs", job_id, tenant_id)


@app.post("/api/v1/jobs/{job_id}/cancel")
def cancel(job_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, db, _ = deps
    job = owned(db, "jobs", job_id, tenant_id)
    if job["state"] in {"QUEUED", "RUNNING"}:
        state = "CANCELED" if job["state"] == "QUEUED" else "CANCEL_REQUESTED"
        db.execute(
            "UPDATE jobs SET state=?,updated=? WHERE id=? AND state IN ('QUEUED','RUNNING')",
            (state, time.time(), job_id),
        )
        db.event(job, "cancel.requested", {"state": state})
    return owned(db, "jobs", job_id, tenant_id)


@app.post("/api/v1/jobs/{job_id}/retry", status_code=202)
async def retry(job_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    settings, db, _ = deps
    job = owned(db, "jobs", job_id, tenant_id)
    if job["state"] != "FAILED":
        raise HTTPException(409, "只能重试失败任务")
    db.execute(
        "UPDATE jobs SET state='QUEUED',error=NULL,attempts=0,updated=? WHERE id=? AND state='FAILED'",
        (time.time(), job_id),
    )
    return await schedule(settings, {"job_id": job_id, "revision_id": job["revision_id"], "state": "QUEUED"})


@app.get("/api/v1/jobs/{job_id}/events")
async def events(
    job_id: str, request: Request, after: int = 0, tenant_id=Depends(tenant), deps=Depends(dependencies)
):
    _, db, _ = deps
    owned(db, "jobs", job_id, tenant_id)
    try:
        initial = max(after, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        raise HTTPException(422, "Invalid event cursor")

    async def stream():
        cursor = initial
        while not await request.is_disconnected():
            rows = db.all(
                "SELECT * FROM events WHERE tenant=? AND job_id=? AND seq>? ORDER BY seq LIMIT 100",
                (tenant_id, job_id, cursor),
            )
            for row in rows:
                cursor = row["seq"]
                yield f"id: {cursor}\nevent: update\ndata: {encode(row)}\n\n"
            if len(rows) == 100:
                continue
            state = db.one("SELECT state FROM jobs WHERE id=?", (job_id,))["state"]
            if state in {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELED"}:
                yield f"event: done\ndata: {encode({'state': state})}\n\n"
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.get("/api/v1/assets/{asset_id}")
def asset(asset_id: str, download: bool = False, tenant_id=Depends(tenant), deps=Depends(dependencies)):
    _, _, storage = deps
    try:
        a, path = storage.get(tenant_id, asset_id)
    except (KeyError, FileNotFoundError):
        raise HTTPException(404, "Asset not found")
    return FileResponse(
        path,
        media_type=a["mime"],
        filename=a["filename"] if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


register_material_routes(app, dependencies)

static = ROOT / "apps/studio/dist"
if static.exists():
    app.mount("/", StaticFiles(directory=static, html=True), name="studio")
