# V2 交付与复现指南

本次续建基于 V1，源码与文档一并更新。基础创作流程继续沿用 README；最新事实以 docs/scope.md 与 docs/verification-v2.json 为准。

## 安装与运行

1. 安装 Python 3.12、Node 20.19+、FFmpeg，运行 `python scripts/bootstrap.py`。
2. `cp .env.example .env`，运行 `.venv/bin/python scripts/dev.py`，打开 http://127.0.0.1:5173。
3. 在界面输入提示词、ZIP 或公开 Git 仓库，先生成分镜，确认旁白后再生成视频。每次修改保存独立版本。
4. 时长模式可选目标、精确、最大；精确模式以视频帧数保证，AAC 封装可能带数毫秒尾部填充。旁白不足时会保留画面，过长只在上限内加速，否则明确失败。

依赖下载需要网络；初次运行不是免安装。未安装语音环境时默认开发配音或明确字幕版，正式配音需下述配置。

## 正式男声与真实对齐

```bash
python -m venv .speech-venv
.speech-venv/bin/pip install torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cpu
.speech-venv/bin/pip install -r services/qwen/requirements.txt -r services/alignment/requirements.txt
.speech-venv/bin/python scripts/download_speech_models.py
```

Linux 安装 `libseccomp2`、FFmpeg，必要时安装 sox；GPU 部署使用相应 PyTorch wheel，需单独验证驱动。

在项目根目录设置绝对路径：

```bash
export QWEN_BASE_MODEL="$PWD/.models/qwen-base"
export QWEN_REFERENCE_WAV="$PWD/assets/voices/professional-male/reference.wav"
export QWEN_REFERENCE_TEXT="$PWD/assets/voices/professional-male/reference.txt"
export QWEN_SERVICE_KEY=替换为至少24字符的独立随机密钥
.speech-venv/bin/python -m uvicorn services.qwen.server:app --host 127.0.0.1 --port 7861
```

另一个终端在 `.env` 设置 `EXPLAINER_TTS_ENGINE=qwen`、`EXPLAINER_TTS_KEY`（与服务相同）、`EXPLAINER_TTS_REVISION=professional-male-v2`、`EXPLAINER_ALIGNMENT_ENGINE=stable-ts`、`EXPLAINER_ALIGNMENT_PYTHON=/绝对路径/.speech-venv/bin/python`、`EXPLAINER_ALIGNMENT_MODEL=/绝对路径/.models/tiny.pt`。重启 API/Worker。实际验证使用 Base 0.6B；CPU 可运行但不保证实时。tiny 适合验证，正式项目可配置更大本地 Whisper 权重并抽查对齐质量。

## 真实页面与交互

界面运行策略支持自动识别、静态 Web、Node Web/CLI、Python API/CLI。框架依赖需事先进入沙箱镜像的离线缓存，缺依赖明确失败。React/Vue 示例已经运行，不能由此推断任意全栈都可零配置运行。

可在 ZIP 中加入 `explainer.json`，或者在界面动作框输入数组：

```json
{"kind":"static-web","entry":"index.html","actions":[{"kind":"click","target":"#open-ai"},{"kind":"assert_visible","target":"#ai-panel"}]}
```

动作仅允许 click/fill/press/select/assert_visible/assert_text/assert_width_increased/wait_visible，selector 使用 Playwright 定位。API 请求可在同文件 requests 数组指定 method/path/expected_status。运行计划和动作结果保留在运行报告。

构建 `docker build -t explainer-sandbox:1.0.0 infra/sandbox`，按 docs/deployment.md 在专用 Worker 启用沙箱并配置 runsc。API 不挂载 Docker socket。当前环境无 Docker，这一步没有实测；不得用宿主机直接运行用户上传代码作为替代。

## 共享存储与编排

- `.env` 配置 EXPLAINER_DATABASE_URL=postgresql://…，EXPLAINER_STORAGE_BACKEND=s3 与 S3 配置，预先创建对象桶。
- 可用 `docker compose -f compose.shared.yaml up --build` 启动 PostgreSQL、独立 API/Worker；S3 为预配置外部服务。默认不开源码执行。密码若有 URL 保留字符需编码。
- SQLite 数据不会自动搬到 PostgreSQL；迁移应先备份、停止写入，以逻辑方式导入各表并重置 events 序列，校验行数和对象哈希后切换。该迁移流程尚无自动工具，不应直接改地址后认为旧任务已迁移。
- Temporal：先部署服务/namespace，配置 EXPLAINER_SCHEDULER=temporal 与地址、队列；Worker 启动用 `python -m explainer.temporal_worker`，API 继续用 uvicorn。compose.shared 默认用本地数据库租约 Worker；切换 Temporal 时必须同步修改 worker command。
- V2 元数据新增 audio_timings 表，启动自动以幂等建表补充；原有 SQLite 记录不被清空。发布前仍需备份。

## 验收证据

- `docs/verification-v2.json` 汇总真实执行结果，`docs/verification-v2/` 保存分类报告。
- `examples/generated/qwen-v2/` 是实际 20 秒、600 帧的 Qwen 男声样片、WAV、SRT、脚本和可导入工程。
- `scripts/verify_narrated_v2.py`、`verify_temporal_v2.py`、`verify_storage_v2.py`、`verify_project_runners_v2.py` 为可重复集成验收。分别需要本地模型/Chrome、Temporal CLI、Moto/PGlite、受控 npm 缓存；不要误认为基础单元测试自动涵盖全部基础设施。

仍需目标部署环境完成：Docker 镜像与 gVisor、原生 PostgreSQL 多连接抢占/崩溃恢复、真实对象存储和外部模型、私有网络与 TLS 配置。组织 SSO/RBAC/计费和移动/桌面运行器不在已实现清单。

原生共享基础设施并发验收脚本：`scripts/verify_shared_deployment.py`，仅对专用验收资源运行，详细命令见 docs/acceptance.md。
