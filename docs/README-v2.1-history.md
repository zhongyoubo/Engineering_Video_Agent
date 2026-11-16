# Explainer Studio

一个可运行的通用讲解视频创作应用：输入提示词、ZIP 源码或公开 Git 仓库，生成内容分析、证据、脚本分镜、配音、字幕、动画和 MP4，并支持编辑、新版本、源码更新与工程包导入导出。

本交付是 **V2.1 原生 Agent 适配版**。`docs/design-baseline.md` 是完整目标设计；`docs/scope.md` 明确本版已实现、配置后可用、未在本环境验证及后续扩展项。不会将任意项目都能真实运行作为承诺。

V2 新增通用项目运行计划与交互断言、真实逐词对齐、严格帧数时长、分阶段 Temporal、PostgreSQL/S3 适配。完整验收与部署步骤见 `docs/v2-delivery.md`；容器隔离与原生 PostgreSQL 多连接验收仍需部署环境执行。

新增 Claude Code / Codex 原生 CLI 执行适配、声明式动画设计与原生场景修改。配置与真实推理验收见 `docs/native-agents.md`；本环境尚未进行带凭据的原生推理联调。

## 从哪里开始

- 使用：本文 → `docs/user-guide.md`。
- 架构：`docs/architecture.md` → `docs/adr/`。
- 开发：`docs/contributing.md`、`docs/adapters.md`、`packages/contracts/`。
- 部署：`docs/deployment.md`、`docs/security.md`。
- 验证：`docs/acceptance.md`、`docs/verification-v2.1.json`。
- API：启动后 `/api/docs`，静态契约见 `packages/contracts/openapi.json`。

## 快速启动：本地开发

要求 Python 3.11+、Node.js 20.19+、FFmpeg（含 ffprobe）。Linux/WSL 推荐；Windows 推荐下面的 Docker Desktop 方式。

```bash
python scripts/bootstrap.py
.venv/bin/python scripts/dev.py
```

打开 http://127.0.0.1:5173 ，使用终端显示的本地访问密钥登录。密钥自动保存在 `.data/access-token`，不随交付包分发。macOS/Linux 命令如上；Windows 本地 Python 路径为 `.venv\Scripts\python.exe`，但源码隔离执行和进程树管理推荐放在 Docker/WSL 中。

若希望完全离线运行，需事先准备 Python/npm 依赖、Chrome 和模型；“本地生成不调用模型”不代表第一次安装无需网络。

### 本地声音

安装 `espeak-ng` 可直接生成普通话或英文开发旁白，例如 Debian/Ubuntu：

```bash
sudo apt-get update
sudo apt-get install ffmpeg espeak-ng
```

没有 eSpeak 时仍能生成字幕版视频，并在质量报告中明确显示缺少声音。eSpeak 是开发音色，不等同于正式专业男声。正式音色请按 `docs/voice.md` 配置 Qwen3-TTS 服务；模型权重不包含在交付包中。

### 可选配置

```bash
cp .env.example .env
```

- 不配置模型：本地规则生成有依据的基础脚本，适合验证完整流程。
- 配置模型：设置 `EXPLAINER_ALLOW_EXTERNAL_MODEL=true`、`MODEL_URL`、`MODEL_NAME`、`MODEL_KEY`（完整变量名见 `.env.example`）；可生成更深入的任意主题讲解。
- 配置 Qwen：`EXPLAINER_TTS_ENGINE=qwen`，设置已启动的本地语音服务地址与服务密钥。
- 指定 Chrome：设置 `EXPLAINER_CHROME_EXECUTABLE` 为绝对路径。

## 快速启动：Docker Desktop / Linux Docker

```bash
cp .env.example .env
# 将 .env 中 EXPLAINER_API_TOKEN 设置为唯一随机值（至少 24 字符）
docker compose up --build
```

打开 http://127.0.0.1:8000 ，访问密钥为 `.env` 中设置的值。镜像安装 FFmpeg、eSpeak、Chrome 并打包前端。本环境没有 Docker，镜像构建和隔离执行未做实际集成验证，部署时请依照 `docs/deployment.md` 执行验收。默认不挂载 Docker Socket、不启用源码执行。

## 一个完整创作流程

1. 登录后选择「一个想法」或「一份源码」。
2. 输入标题、讲解要求，设置受众、语言、时长、音色与主题。
3. 选择「先生成脚本分镜」或「生成完整视频」。
4. 在编辑器查看实时预览、证据和质量报告。
5. 编辑旁白、标题、画面类型；保存时创建新版本。
6. 下载 MP4、脚本、SRT、质量报告和可编辑工程。
7. 在「视频与版本」导入可编辑工程；源码工程可点击「更新源码」。

示例：`examples/source-demo.zip` 是 Python 同步示例，`examples/static-web-demo.zip` 是隔离 Web 录制示例。归档内相对入口分别是 `sync_demo.py` 和 `index.html`。

## 项目结构

```text
apps/api/                  FastAPI、领域协议、队列、业务服务、适配器及测试
apps/studio/               React 创作台、播放器、编辑器
packages/contracts/        生成的 JSON Schema 与 OpenAPI
packages/video/            共用视频组件、时间线类型、Remotion 渲染入口
services/qwen/             可选独立 Qwen3-TTS 服务与音色设计脚本
infra/sandbox/             隔离 Web/Python 执行与捕获镜像
assets/fonts/              视频/编辑器共用字体及其许可证
scripts/                   初始化、启动、诊断、契约导出、媒体验收
examples/                  可复现输入及实际生成样例
tests/browser/             浏览器端到端测试
docs/                      架构、接口、规范、部署、安全、验收及原始设计
```

## 验证命令

```bash
.venv/bin/python -m pytest apps/api/tests -q
.venv/bin/ruff check apps/api/src apps/api/tests
npm run typecheck
npm run build
npm run test:ui
.venv/bin/python scripts/media_smoke.py
.venv/bin/python scripts/media_smoke.py --source --output .source-smoke
```

`scripts/media_smoke.py` 真正生成 MP4，不是模拟渲染；输出在 `.media-smoke/deliverables`。浏览器测试需要 Chrome；若 Playwright 自带 Chrome 未安装，设置 `CHROME_EXECUTABLE`。媒体测试的同名环境变量会传给渲染器。

## 本版边界

- 模型和 Qwen 服务可替换；未配置时只提供基础模板脚本和开发音色/字幕。
- 源码支持通用文本分析，Python 使用 AST，其他语言提供有限符号/目录观察，不虚称完整调用图。
- 真实运行适配器目前是静态 Web 与标准库 Python CLI，不自动安装任意项目依赖。
- 字幕使用明确标记的句级长度估算，不宣称已实现强制语音对齐。
- 数据库是 SQLite WAL，支持同机多个 Worker、租约、恢复和写入 fencing；不是多节点 SaaS 数据库。
- Temporal 是可选调度适配器；本交付仍使用单机元数据。生产多节点需替换共享事务存储并完成部署验证。
- Remotion 及第三方模型、字体、编码器有各自许可。见 `THIRD_PARTY_NOTICES.md`，不要将本项目代码许可证当作这些组件的许可。

