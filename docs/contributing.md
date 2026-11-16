# 工程目录与文件规范

## 分层依赖

- domain 不依赖 HTTP、数据库或前端。
- API 负责输入校验与授权，业务处理进入 services/adapters。
- db/storage 负责持久化；文件路径只在服务端构造。
- React Studio 通过 HTTP 使用工程，不直接读取数据库和文件系统。
- video 包不依赖 API 服务，靠 props 与素材引用驱动。
- Qwen 独立环境，避免巨大模型依赖进入普通 API 安装。

## 命名

Python 文件/函数 snake_case，类 PascalCase；TypeScript 类型/组件 PascalCase；JSON/API 使用 snake_case；资源 ID 带固定前缀，不能由用户拼接为路径。文档英文文件名，正文可中文，避免空格和不稳定本机绝对路径。

## 文件管理

每个文件聚焦一类职责。协议以 Pydantic 为源，生成的 JSON Schema 和 OpenAPI 同批更新。新场景需要同步 Python 枚举、TS 联合类型、Renderer 和测试。不要只更新一端造成静默不兼容。

不得提交 .env、access-token、数据库、运行素材、node_modules、虚拟环境、模型权重、真实个人参考录音和用户源码。示例数据必须自造且可公开。

## 格式与检查

```bash
.venv/bin/ruff format apps/api/src apps/api/tests
.venv/bin/ruff check apps/api/src apps/api/tests
npx prettier --write apps/studio packages/video tests/browser scripts/*.mjs
npm run typecheck
.venv/bin/pytest apps/api/tests -q
npm run test:ui
```

改后端协议后运行 `python scripts/export_contracts.py`。改视频场景后运行至少一个真实媒体测试。高风险边界写有意义的错误/隔离/恢复测试，不用仅镜像实现的快照充数。

## 错误与日志

前端提示可读错误，不返回 API key、原始模型请求或未经脱敏的堆栈。事件携带 job/stage，不依赖聊天记录恢复任务。错误必须可分类；不将失败结果包装为成功。

## 架构变更

重大偏离基线记录 ADR，内容包括问题、选择、替代方案、边界和验证证据。保持接口、代码、文档和测试一致；不要把只写接口的功能放进已完成列表。


## V3 engineering changes

Read root AGENTS.md, Roadmap.md and docs/design/. Keep contracts, generated schemas, UI, tests and deployment docs in sync. Engineering actions must use the mediated filesystem and isolated tools; never add a host execution fallback. Source/props changes invalidate gates. Distinguish authored fixtures, true model inference, visual review and human acceptance in every report.
