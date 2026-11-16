# Explainer Studio — Engineering Video Agent

输入项目源码或提示词，让原生 Agent 完成内容策划、脚本与动效设计，编写真实 Remotion/React/TSX 工程，通过构建、试渲染、图像审查与修复后交付视频和完整源码。

本版在 V3 工程闭环上增加 V4 视觉制作能力：1080p/4K 输出规格、两套设计体系、七类图解积木、旁白短语驱动的动效事件、连续镜头预览、实际波形、版本差异和可选 MCP。Agent 仍可自由编写镜头与组件，不受这些积木限制。旧模板方式作为显式兼容入口保留。

## 从这里开始

- **AGENTS.md**：工程协作、执行和验收规则（标准文件名，不创建 Windows 上冲突的大小写副本）。
- **Roadmap.md**：里程碑、实际完成情况与待部署验收。
- **docs/design/README.md**：系统、领域、执行、协议与设计说明索引。
- **docs/engineering-operations.md**：完整安装、镜像、模型、操作和验收步骤。
- **docs/verification-v3.json**：本次执行证据与未验证项。
- **docs/design/visual-explainer-v4.md**：本次新增能力、使用方式与边界。
- **docs/verification-v4.json**：V4 的实际检查与未验证项。

## 安装与启动

要求 Python 3.12、Node 20.19+、FFmpeg；工程任务需要专用 Docker/gVisor Worker。

```bash
python scripts/bootstrap.py
.venv/bin/python scripts/dev.py
```

打开 http://127.0.0.1:5173，用终端显示的访问密钥登录。Windows 推荐 WSL2 + Docker Desktop。先启动界面不代表模型、渲染和语音已配置。

随后按 docs/engineering-operations.md 构建原生 Agent 与独立渲染镜像，配置对应 API 凭据、Qwen-TTS 和真实对齐模型。未配置时明确失败，不会悄悄输出模板或换成开发音色。模型与安装依赖不包含在源码 ZIP；首次准备需要网络。

## 制作流程

1. 理解源码/主题并形成依据。
2. 原生 Agent 生成制作方案、旁白、分镜与逐镜头动效设计。
3. Qwen 与真实对齐得到实际音轨和帧预算。
4. Agent 写入 TSX，选择构建、试渲染、审查和修复操作。
5. 同一源码 hash 的构建、预览、审查全部通过后才最终渲染。
6. 下载 MP4、WAV、SRT、脚本、报告和可继续编辑的 Remotion 工程。

UI 和 `/api/v3/videos` 默认工程模式；`/api/v1/videos` 为向后兼容保留模板默认。正式模式默认 Qwen，也允许明确选择已配置的 Edge/Ming，并要求真实对齐；不会自动换供应商。声音自然度需要试听验收。草稿模式需明确选择。原生运行使用管理员 API key，不自动使用订阅登录。

## V4 快速使用

创建页选择输出分辨率、设计体系和语速；有音轨后在“音画时间轴”查看实际波形、镜头预览和旁白同步事件。修改另存新版本，与上一版比较。工程预览始终使用实际渲染产物，不在主站直接执行模型生成的 JS。

API 可增加 `render_profile: {"resolution":"4k","fps":30}`、`design_pack: "editorial_warm"`、`voice_spec: {"speed":1.0,"revision":"1"}`。Qwen 克隆服务使用部署时固定的参考声音；更换模型/参考文件需更新服务修订号，不能伪装成已经支持任意音色参数。

固定源码渲染检查：`CHROME_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/verify_visual_v4.py`。它生成三个无配音草稿镜头与 4K 视频，属于真实渲染检查，不是原生模型/TTS 验收。

可选 MCP 在独立环境安装 `pip install -e 'apps/api[mcp]'`，设置 `EXPLAINER_MCP_URL` 和 `EXPLAINER_MCP_TOKEN` 后运行 `python -m explainer.mcp_server`。七个工具复用同一任务 API；见 V4 设计文档。MCP 并未开放任意 shell 或修改现有原生 CLI 的受限工具配置。

## 项目结构

| 目录 | 职责 |
|---|---|
| apps/api/src/explainer/services/engineering/ | 策划、工程动作、工作区、校验与工具控制 |
| apps/api/src/explainer/adapters/ | 可替换原生 Agent、语音、对齐和源码执行适配 |
| services/native_agent/ | 容器内 CLI 驱动、状态归一化和图像上下文 |
| packages/engineering-template/ | 可独立交付的工程骨架、可信字幕/音频/字体入口与渲染器 |
| infra/engineering-render/ | 无凭据、断网的构建与渲染容器 |
| apps/studio/ | 模式选择、脚本编辑、真实预览和交付下载 |
| packages/contracts/ | 自动生成的 API、领域和 Agent JSON Schema |
| docs/、goals/ | 设计、部署、范围、施工与实测记录 |

## 验证与当前边界

运行 `.venv/bin/python scripts/check.py` 与 `npm run test:ui`。`scripts/verify_engineering_fixture.py` 对固定可信源码实测编译错误、修复、关键帧和完整渲染；它不是实际供应商推理，也不是宿主机运行用户代码的替代路径。

目标环境用 `scripts/verify_engineering_deployment.py` 分别验收 Codex / Claude Code；该脚本会消耗对应供应商额度。

当前环境没有 Docker/gVisor 和供应商凭据，所以未完成真实原生模型到视频的集成验收。人工完整观看、试听、模型输出质量、每类项目的运行依赖仍需验收。框架已提供工程闭环，不能承诺任意项目零配置运行或每次自动达到专业成片质量。

## 本项目介绍片与三个参考视频复查

`examples/project-intro/` 提供固定编排的本项目介绍片测试：真实源码导入、工作台录制、公开 README 旁白、实际词时间戳、Remotion 编译/预览/4K 渲染与可编辑工程。复现方法见该目录 README，分析与边界见 `docs/reference-review-and-self-test-cn.md`。样片使用固定编排，不作为原生模型自动制作验收。

本次补充扇形总览布局、按图解类型限制元素数与文字长度、修正长标签显示及模板预览暂停在空白首帧的问题。Edge 可选依赖为 `pip install -e 'apps/api[edge]'`；需显式选择 Edge，支持 `EXPLAINER_EDGE_VOICE` 和可选 `EXPLAINER_TTS_PROXY`。其实际词边界通过文本/时间校验后可驱动画面；显式选择 `stable-ts` 时仍需本地模型，不把 Edge 时间戳称为 Whisper。没有自动改用其他配音服务。
