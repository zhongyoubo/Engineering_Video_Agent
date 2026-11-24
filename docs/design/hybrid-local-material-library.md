# 混合本地素材库 · PNG 首版

仓库内继续保存经过审查、固定版本和哈希的组件/PNG/GLB 精选包。增长中的个人图片库放在仓库外，由管理员通过 `EXPLAINER_LOCAL_MATERIAL_DIR` 配置绝对路径。该目录按租户分隔：`<root>/<tenant>/index.json` 与 `files/<sha256>.png`。未配置时 API 返回空清单，现有精选包和浏览器上传照常工作。

本版只开放单帧 PNG；登记命令会用项目现有的 `canonical_png` 校验尺寸、字节预算、解码和元数据剥离，写入内容寻址文件与原子更新的索引。每条记录必须有稳定 ID、标题、来源与授权说明。示例：

```powershell
.venv\Scripts\python.exe scripts/local_material_library.py --root D:\VideoAssetLibrary add --id agent-notes --title "Agent 笔记" --origin "作者自制" --rights "项目内使用" --file D:\素材\notes.png
.venv\Scripts\python.exe scripts/local_material_library.py --root D:\VideoAssetLibrary list
```

给 API 设置 `EXPLAINER_LOCAL_MATERIAL_DIR=D:\VideoAssetLibrary`。容器部署时，将库以只读方式挂载到 API，并设置容器内的绝对路径。租户目录名必须与配置完全一致，两个租户名忽略大小写后仍须不同。工作台按页展示本地素材，预览使用最长边 320 像素的 PNG 和私有 ETag 重验证。创建工程后，API 再次核对项目所有权、素材 ID 与勾选时的源 SHA。事务内以同一项目、素材 ID 和源 SHA 去重。图片的来源、授权、源 SHA 与本地 ID 随 `generated-assets.json` 的 `provider_identity.local_material` 导出。渲染器只使用项目内注册的 PNG。

接口：`GET /api/v3/local-materials`、`GET /api/v3/local-materials/{id}/preview`、`POST /api/v3/projects/{project_id}/local-materials/{id}/import`。接口均需租户身份；导入还需目标项目所有权。工作台最多合并选用 24 张本地及上传图片。其他文件格式仍走已有精选包/工程接口，本版不把它们标为已支持本地导入。选中图片进入项目后，后续源码、素材和审查哈希仍沿用项目图片链路。

验证覆盖 CLI 实际登记、缩略图与重验证、租户与项目隔离、畸形索引、顺序及并发导入、源文件篡改拒绝、回执恢复和 ZIP 来源字段。真实原生 Agent 选图质量、部署目录挂载及全片试听仍待验收。
