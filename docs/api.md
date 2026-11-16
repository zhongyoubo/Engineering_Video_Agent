# HTTP API 与数据契约

启动后查看 `/api/docs`。仓库内 `packages/contracts/openapi.json` 是可离线导入的 OpenAPI；Pydantic 是源协议，运行 `python scripts/export_contracts.py` 更新 JSON Schema。不要手工修改生成文件。

## 认证

`Authorization: Bearer <workspace-key>`，或调用 `POST /api/session` 交换 HttpOnly、SameSite=Strict Cookie。默认单个本地租户，额外租户在 `EXPLAINER_TENANT_KEYS` 中配置唯一密钥。没有多用户组织角色和 SSO；不要把工作空间密钥用作公开 SaaS 身份系统。

## 主接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/health | 最小健康状态 |
| GET | /api/v1/capabilities | 脱敏后的适配器与运行能力 |
| POST/GET | /api/v1/projects | 创建/列出项目 |
| POST/GET | /api/v1/projects/{id}/inputs | 上传 ZIP/列出输入快照 |
| POST | /api/v1/videos | 创建制作任务，支持 Idempotency-Key |
| GET | /api/v1/jobs | 最近 100 项任务 |
| GET | /api/v1/jobs/{id} | 当前状态 |
| GET | /api/v1/jobs/{id}/events | SSE，支持 Last-Event-ID 或 after |
| POST | /api/v1/jobs/{id}/cancel | 取消 |
| POST | /api/v1/jobs/{id}/retry | 从检查点重试失败任务 |
| GET | /api/v1/revisions/{id} | 工程、内容、分镜、质量与输出引用 |
| POST | /api/v1/revisions/{id}/fork | 版本派生、脚本编辑与重新导出 |
| POST | /api/v1/revisions/{id}/changes | 自然语言修改当前场景 |
| POST | /api/v1/revisions/{id}/source | 更新源码并派生版本 |
| POST | /api/v1/projects/{id}/import | 导入平台可编辑工程包 |
| GET | /api/v1/assets/{id} | 授权媒体；download=true 附件下载 |

## 调用示例

```bash
curl http://127.0.0.1:8000/api/v1/projects \
  -H "Authorization: Bearer $EXPLAINER_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"API tutorial"}'
```

```json
{
  "project_id": "prj_returned_by_server",
  "brief": {
    "title": "理解 API",
    "prompt": "用天气查询解释请求、服务处理和响应。",
    "language": "zh-CN",
    "audience": "beginner",
    "target_seconds": 60,
    "voice": "auto",
    "mode": "automatic",
    "accent": "blue",
    "runtime": "none"
  }
}
```

向 `/api/v1/videos` POST 上述 JSON，返回 202、job_id 和 revision_id。不要猜测资源 ID。

## 错误与幂等

标准错误包含 `error.code` 和 `error.message`。校验错误不返回敏感输入值。未知/越权资源返回 404。

相同 Idempotency-Key 与相同请求返回同一任务；不同请求体返回 409。额外租户键和素材不会跨租户匹配。配额按活跃任务数限制，默认每租户三项。

## 状态

QUEUED → RUNNING → SUCCEEDED/PARTIAL/FAILED。取消为 CANCELED 或先 CANCEL_REQUESTED。阶段检查点在同一 job 中恢复；公开的 retry 仅允许 FAILED。

SUCCEEDED 表示当前模式完成，例如 storyboard 模式只要求分镜，不代表已有 MP4。PARTIAL 表示视频可交付但必选声音或真实运行缺失。质量报告仍可能有非阻断警告。

## 限制

本版不提供任意用户 URL 抓取、Git 凭证导入、Webhook 或外部生产写入 API。模型/TTS 地址是部署者配置，不由提示词指定。

