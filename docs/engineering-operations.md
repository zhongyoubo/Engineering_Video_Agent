# 部署与操作：工程型视频 Agent

## 启动创作台

安装 Python 3.12、Node 20.19+、FFmpeg。执行 `python scripts/bootstrap.py`，再 `.venv/bin/python scripts/dev.py`。访问 http://127.0.0.1:5173，使用终端显示的本地密钥登录。Windows 建议在 WSL2 配合 Docker Desktop 使用 Linux 路径。

创作台可先启动；真正制作需要下述原生 Agent、独立代码执行环境和语音服务。未配置时不会输出模板来冒充工程视频。

## 构建三个独立镜像

在仓库根目录执行：

```bash
docker build -f infra/native-agent/Dockerfile --build-arg PROVIDER=codex -t explainer-native-codex:3.0.0 .
docker build -f infra/native-agent/Dockerfile --build-arg PROVIDER=claude-code -t explainer-native-claude:3.0.0 .
docker build -f infra/engineering-render/Dockerfile -t explainer-engineering-render:3.0.0 .
```

只用一个供应商时只需对应 Agent 镜像加渲染镜像。必须重建 V3 Agent 镜像，V2.1 的旧 driver 不识别工程任务。构建需要依赖网络，任务执行时渲染容器断网。

Worker 在专用 Docker 主机运行，具有 Docker 调度权限；API 不挂载 Docker Socket。默认原生与工程工具容器使用 runsc，需要在主机部署 gVisor；未配置会明确失败。Worker 与 daemon 必须共享同一绝对路径视图，不能把本机目录直接当成远程 daemon 目录。

## 模型和语音配置

从 .env.example 建立私有配置。选择供应商，设置 EXPLAINER_NATIVE_AGENT_PROVIDERS=codex 或 claude-code，以及对应 EXPLAINER_CODEX_API_KEY / EXPLAINER_CLAUDE_API_KEY。可分别指定 CODEX_AGENT_MODEL / CLAUDE_AGENT_MODEL（均有 EXPLAINER_ 前缀）。只在 Worker 配置供应商密钥。

原生模型容器需要访问模型服务，配置专用出口网络/代理；bridge 并不等于域名白名单。禁止将模型密钥传入生成代码执行容器。当前仅支持管理员 API-key 模式，不自动使用订阅/OAuth 登录，也没有每用户供应商凭据保险箱。

Qwen 启动与模型下载见 docs/v2-delivery.md 与 docs/voice.md。设置 EXPLAINER_TTS_URL、TTS_KEY、TTS_REVISION，并配置 ALIGNMENT_PYTHON 与 ALIGNMENT_MODEL（均带 EXPLAINER_ 前缀）。本版保留专业合成男声参考，但正式音色仍须试听选择。不能把加载模型与音频可解码说成听感已经合格。

## 工作流程

1. 工程 Agent 模式上传源码或填写主题，先选择“先生成脚本分镜”。
2. 审阅制作方案、每镜头画面/动效和旁白；保存/修改场景。
3. 生成视频：配音和对齐确定实际帧数，然后编写工程、编译、试渲染、审查、修复。
4. 查看工程动作和实际预览，下载 MP4、WAV、字幕、报告与完整源码。
5. 源码变化后重新验证。人工观看并试听全片，最终决定是否适合发布。

## 有限执行与恢复

ENGINEERING_MAX_STEPS 默认 18，每次工具观察或拒绝都计入；ENGINEERING_TOOL_TIMEOUT 默认 300 秒，原生调用超时见 NATIVE_AGENT_TIMEOUT。Claude 的估算预算是单次调用约束，不是整个项目的硬账单上限；一次工程任务有多次调用。Codex 当前只限制时长与次数。请同时设置供应商侧预算。

租约/fence、取消、检查点沿用已有机制；每步工程状态同步至素材存储。源码变更使旧检查失效。崩溃可能重放尚未提交的模型请求；原生会话不会在供应商间迁移。Temporal 当前每个业务阶段有 45 分钟超时，长任务需结合目标规模调整并验收。

## 验收

```bash
.venv/bin/python scripts/check.py
npm run test:ui
CHROME_EXECUTABLE=/你的Chrome路径 .venv/bin/python scripts/verify_engineering_fixture.py
.venv/bin/python scripts/verify_engineering_deployment.py --provider codex --draft
```

最后一个命令会真实调用配置供应商并消耗其额度；去掉 --draft 使用正式 Qwen 与对齐。两个供应商、源码捕获、取消中途推理、跨 Worker 恢复、真实听感需分别验收。

本次环境没有 Docker 与供应商凭据，未执行真实原生模型到视频联调。固定可信夹具实测了编译错误、修复、9 张关键帧、600 帧成片和整片解码。此夹具只允许固定自编源码，不是生产环境绕过隔离的开关。

### Semantic renderer packaging follow-up

Rebuild the engineering render image when pulling the semantic-scene changes: render.mjs
imports the protected review-plan.mjs, and both must be installed in /opt/engine. The
Dockerfile now copies this dependency explicitly. A local fixed render is not an image
build/run test. Routine backend tests check the transitive local runtime imports against
Dockerfile COPY inputs; still run the isolated deployment acceptance on the target Worker.
