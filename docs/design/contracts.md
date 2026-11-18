# 工程契约、目录和交付物

JSON Schema 均由 Pydantic 导出至 packages/contracts/，不要手工修改生成文件。

## 创建工程任务

`POST /api/v3/videos`：默认 engineering、codex、professional。professional 将 auto 音色解析为 Qwen 并强制真实对齐，不允许 eSpeak/none。指定 draft 才可以生成无配音工程验收草稿。`mode=storyboard` 只做前期策划，不调用构建/渲染工具。

```json
{"project_id":"项目ID","brief":{"title":"项目讲解","prompt":"面向工程师，解释核心机制并展示实际页面","agent_engine":"codex","target_seconds":90,"duration_mode":"max","mode":"automatic"}}
```

旧 `/api/v1/videos` 保留模板兼容默认；明确传入 video_mode=engineering 也可使用。原生 Agent、Qwen 与渲染环境未配置时明确失败。首次部署先创建 storyboard 任务，审阅 production-plan.json，再保存/渲染该版本。

## 工程动作

```json
{"action":"write_files","summary":"实现项目流程联动动画","files":[{"path":"src/Video.tsx","content":"真实 React/TSX 源码"}],"review":null}
```

其他动作：build、render_preview、review、finish。只有 write_files 可以携带文件，只有 review 可以携带审查结果。审查包含 accepted、legibility、visual_explanation、timing、issues 和 inspected_frames；评分至少 4、无问题，且关键帧列表与实际观察一致才能通过。

文件工具仅允许 src 下的 .ts/.tsx/.css 视觉代码；禁止修改 index.tsx、Root.tsx、contracts.ts、隐藏文件、依赖清单、脚本、props 和公共资产。拒绝路径逃逸、重复路径、过大补丁和替换字符。

## 工程目录

| 路径 | 内容 |
|---|---|
| src/Video.tsx | Agent 编写的主视觉组件，默认导出，接收 VideoProps |
| src/scenes/、src/components/ | Agent 可建立的镜头与复用视觉组件 |
| src/Root.tsx、index.tsx、contracts.ts | 平台控制的注册、字体、音轨、字幕与类型 |
| public/ | 授权画面、逐镜头音频和固定字体 |
| props.json | 实际编译后的时间线与素材引用 |
| package.json、package-lock.json | 固定依赖，可复现安装 |
| render.mjs | 平台控制的 tsc、bundle、关键帧和成片工具 |
| production-plan.json | 策划、脚本与逐镜头视觉/动效设计 |
| authoring-journal.json、visual-review.json | 构建、观察、修复与审查证据 |

## 输出角色

video、script、subtitles、narration、quality、alignment 保持原有含义。新增 production_plan、engineering_project、visual_review、authoring_journal、engineering_preview、keyframes；engineering_state 为平台恢复状态，不作为可执行指令信任。

`remotion-project.zip` 是独立完整源码工程，支持解压后 npm ci / npm run check / npm run preview / npm run render。应用原有“导入工程”读取 IR 工程包，不会把外部 Remotion 代码自动导入为受信执行状态；外部源码应作为新输入再走工程校验。应用内派生版本可以复用父版本源文件状态。

场景锁定保护分镜字段与时间预算；本版尚未对共享 TSX 样式建立逐场景像素不变证明。修改共享组件后应重新审阅所有关键帧。

## Semantic scenes and asset actions

Optional semantic_scene and compiled_semantic_events preserve historic saved boards. Typed
SemanticScene/Entity/Event/Expectation and VisualIntent specify data, references, state and
observable outcomes. AssetRequirement supports only the advertised provider capabilities.
EngineeringAction.request_assets creates materials through the controller; inspect_asset
requires a registered workspace ID and verifies actual file bytes. AssetImage references
props.generated_assets by ID, never an arbitrary URL. The registry owns that props mapping.

VisualReview.semantic_expectations must exactly list all scene_id:expectation_id keys and
semantic_accuracy must reach four for causal semantic scenes. Existing source/build/preview,
continuous-motion and publication gates still apply. Exported contracts are in
packages/contracts; see design/semantic-production.md for boundaries and fixed verification.
