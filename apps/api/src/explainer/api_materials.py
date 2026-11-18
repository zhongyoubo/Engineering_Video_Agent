"""Project-owned image ingestion for the engineering asset tool."""

from fastapi import Depends, File, Form, HTTPException, UploadFile
from .security import owned, tenant
from .services.assets.project_images import catalog, put_image
from .services.assets.raster import MAX_IMAGE_BYTES


def register_material_routes(app, dependencies):
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
