# Explainer Studio — Engineering Video Agent

面向知识与技术内容创作者，把主题、资料或项目源码，制作成有清晰主张、依据和观众收益的视频。原生 Agent 完成内容策划、脚本与视觉设计，编写真实 Remotion/React/TSX 工程，通过构建、试渲染、审查与修复后交付成片和完整源码。

本版在 V3 工程闭环上增加 V4 视觉制作能力：1080p/4K 输出规格、两套设计体系、七类图解积木、十一类可组合对象、接口与信号/状态动效、旁白短语驱动的动效事件、连续镜头预览、实际波形、版本差异和可选 MCP。Agent 仍可自由编写镜头与组件，不受这些积木限制。旧模板方式作为显式兼容入口保留。

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

## 自有素材库、独立封面与 Ming 配音

`assets/library/catalog.json` 提供 30 项带版本、来源和校验指纹的代码/字体素材，`GET /api/v1/material-library` 和工作台“环境与能力”可查看；原生策划可选用并记录 `library:<id>@<version>`。详见 `docs/design/material-library-and-speech-cn.md`。

`scripts/verify_project_bookends.py` 为已有自测片补独立 3 秒封面和 4 秒结束页，校验正文指纹后复用，实际生成 71.23 秒 4K 影片，并保留原正文与合成工程。它不重新配音，仍是 Edge 云希。Ming 的新参考音色与种子参数仅完成协议验证；真实服务、音质和对齐仍需验收。

## 自媒体内容制作

以观众收益为中心，支持介绍告知、解释理解、分析评估、观点论证、建议决策、教学操作六类目的。
讲述对象、目标观众和表现形式独立设置；同一个项目可以用不同目的组织内容。
创建页可选择内容目的，填写核心主张、观众收益和账号/栏目名。
原生工程方案增加结构化内容策划；正文围绕主线展开，结尾给出结论或建议。

两条渲染路径均提供独立发布封面与片内开场；首帧主题可读。创作者画面不再
常驻显示“概念讲解”或工具页眉，制作方式与供应商记录保留在工作台和报告。
代码示意/样本来源等必要说明在相关镜头局部显示。可修改封面文案并另存版本，
下载封面 PNG；修改内容意图会重新策划，修改旁白继续触发音轨与时间轴重算。

详情见 `docs/design/creator-production.md`，固定样例验证见
`docs/verification-creator.json`。当前仍支持 16:9；竖屏与方形布局待后续实施。


## 内容定位与分类

- [产品定位与四维分类](docs/product/positioning-and-content-taxonomy.md)：六类观众任务、选题与验收标准。
- [内容策略实现](docs/design/content-strategy.md)：请求、模型解析、叙事结构、质量检查与旧数据迁移。
- [六类样例](examples/content-strategies/)：不同的主张和结构；固定样例不等于模型生成质量验收。

新原生创作者方案记录内容分类理由、观众深度、表现形式、实际分镜结构和验收目标。
创作页面支持辅助目的和版本目标修改；“知识分享”作为广义方向，不再与六类目的混为一层。
自动分类由策划模型理解完整上下文完成；未配置模型时明确保留兼容草稿身份。

策划的结构、素材、证据和发布校验已接入原生 Agent 的限次自动修复；超过次数明确失败。
修改内容目标后，摘要会提示待重新策划并隐藏旧策略；修改标题、语言或制作模式会重建分镜。

## 具体对象、场景与动作

不再把电视、游戏机和音响都画成写着名字的节点。新增可组合对象层：电视、显示器、笔记本、
游戏机、播放器、回音壁、音箱、遥控器、手机、服务器、路由器，支持具体接口、线缆接入、
图像/音频/控制/数据信号、屏幕播放、开关机、声波与音量变化。原生策划按讲解目的组合对象、
初始状态、动作和结果；事件按真实旁白词边界编排。可选原创轻量交互提示音，旁白优先。

`Scene.visual_scene` 是数据协议，不执行上传代码；两条渲染路径复用受保护的对象组件。
Studio 可查看对象与动作、修改标注/旁白锚点及提示音开关；另存版本后重新编排和审核。
未覆盖对象仍可由原生 Agent 编写合适的 SVG/TSX，再经隔离构建/试渲染；不强行套成某个设备。
未部署模型时不会假装已经自动生成任意对象；通用文生图、复杂 3D 和摄影机系统尚未接入。

详见 [对象场景设计](docs/design/object-scenes.md)、[固定样例](examples/object-scenes/) 和
[实际验证](docs/verification-object-scenes.json)。固定场景检查覆盖两条路径的屏幕状态变化、
十一类对象与真实提示音混入；示意动画不代表 HDMI 硬件、120Hz/HDR 或音质实测。

## AI 语义场景与受控素材制作

新增目标输入、对话、Token、上下文、文档片段、检索结果、模型边界、工具调用、任务状态、
证据、操作确认和代码界面等十二类语义组件。`Scene.semantic_scene` 描述对象、真实旁白锚点、
状态变化与可见结果；可以单独组成镜头，也可以用 `bind_to` 绑定到电视、显示器、电脑或
手机屏幕。状态标题、按钮和标注读取同一份状态。旧对象、图解和分镜继续兼容。

原生工程动作新增 `request_assets` / `inspect_asset`：实际制作带中文字体的原创文档 SVG、
同输入 PNG 预览和来源/哈希记录，支持任务检查点恢复、去重、取消及版本失效。原生 Agent
仍需编写真实工程、隔离构建并看图审核。当前素材制作器为受控代码绘制，尚未接入照片、
视频或 3D 生成服务；不会把本对话可用的生图工具冒充项目已接入的能力。

预览按关键语义事件采样动作前、中、后，并覆盖镜头后半段的确认与结果。工作台可编辑
标题/旁白锚点，查看绑定和每段连续预览。RenderPlan 统一登记素材与依赖；目前只有依赖
指纹，没有实现镜头视频缓存或通用 FFmpeg 合成后端。

详见 [语义场景设计](docs/design/semantic-production.md)、[固定样例](examples/semantic-scenes/)
和 `scripts/verify_semantic_scenes.py`。固定样例验证与真实原生模型自动创作验收分别记录。
