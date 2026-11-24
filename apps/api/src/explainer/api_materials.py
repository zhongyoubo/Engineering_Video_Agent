"""Project-owned image ingestion for the engineering asset tool."""

from fastapi import Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from .local_materials import SHA256, catalog as local_catalog, image_bytes
from .security import owned, tenant
from .services.assets.project_images import LocalImageSource, catalog, put_image
from .services.assets.raster import MAX_IMAGE_BYTES, png_thumbnail


def register_material_routes(app, dependencies):
    @app.get("/api/v3/local-materials")
    def local_materials(tenant_id=Depends(tenant), deps=Depends(dependencies)):
        settings, _, _ = deps
        try:
            return {
                "configured": settings.local_material_dir is not None,
                "items": local_catalog(settings.local_material_dir, tenant_id),
            }
        except (OSError, ValueError):
            raise HTTPException(409, "本地素材目录或清单无效，请检查配置与文件")

    @app.get(
        "/api/v3/local-materials/{material_id}/preview",
        response_class=Response,
        responses={200: {"content": {"image/png": {}}}, 304: {"description": "Thumbnail unchanged"}},
    )
    def local_material_preview(
        material_id: str,
        source_sha256: str | None = Query(default=None, pattern=SHA256),
        if_none_match: str | None = Header(default=None),
        tenant_id=Depends(tenant),
        deps=Depends(dependencies),
    ):
        settings, _, _ = deps
        try:
            item, data = image_bytes(settings.local_material_dir, tenant_id, material_id, source_sha256)
            etag = f'"png-320-v1-{item["sha256"]}"'
            headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
            if etag in [tag.strip().removeprefix("W/") for tag in (if_none_match or "").split(",")]:
                return Response(status_code=304, headers=headers)
            return Response(png_thumbnail(data), media_type="image/png", headers=headers)
        except (OSError, ValueError):
            raise HTTPException(404, "本地素材不存在或内容已改变")

    @app.post("/api/v3/projects/{project_id}/local-materials/{material_id}/import", status_code=201)
    def import_local_material(
        project_id: str,
        material_id: str,
        source_sha256: str | None = Query(default=None, pattern=SHA256),
        tenant_id=Depends(tenant),
        deps=Depends(dependencies),
    ):
        settings, db, store = deps
        owned(db, "projects", project_id, tenant_id)
        try:
            item, data = image_bytes(settings.local_material_dir, tenant_id, material_id, source_sha256)
        except (OSError, ValueError):
            raise HTTPException(404, "本地素材不存在或内容已改变")
        try:
            return put_image(
                db, store, tenant_id, project_id, data, item["title"],
                local_source=LocalImageSource(
                    local_material_id=material_id, source_sha256=item["sha256"],
                    origin=item["origin"], rights=item["rights"],
                ),
            )
        except ValueError:
            raise HTTPException(422, "本地素材必须是有效的单帧 PNG，且项目仍有素材名额")

    @app.get("/api/v3/projects/{project_id}/images")
    def images(project_id: str, tenant_id=Depends(tenant), deps=Depends(dependencies)):
        _, db, _ = deps
        owned(db, "projects", project_id, tenant_id)
        return {"items": catalog(db, tenant_id, project_id)}

    @app.post("/api/v3/projects/{project_id}/images", status_code=201)
    async def upload_image(
        project_id: str,
        file: UploadFile = File(...),
        title: str = Form(..., min_length=1, max_length=60),
        tenant_id=Depends(tenant),
        deps=Depends(dependencies),
    ):
        _, db, store = deps
        owned(db, "projects", project_id, tenant_id)
        data = bytearray()
        try:
            while chunk := await file.read(65536):
                data.extend(chunk)
                if len(data) > MAX_IMAGE_BYTES:
                    raise HTTPException(413, "图片超过大小限制")
        finally:
            await file.close()
        try:
            return put_image(db, store, tenant_id, project_id, bytes(data), title)
        except ValueError:
            raise HTTPException(422, "图片必须是有效的单帧 PNG，或项目素材数量超过限制")
