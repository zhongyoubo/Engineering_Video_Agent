# Engineering video Agent implementation

## 复查修复与验证 · 2026-11-24

- Studio 将编辑草稿绑定到当前版本，轮询仅刷新服务器结果。封面回归在用户输入后等待一次真实版本读取，再断言草稿和另存版本均保留新值。Windows 启动脚本与 Playwright 支持独立端口，本轮已配置 Chromium 实跑 20 项，全部通过。
- 精选素材按原始 Git 字节签出，暂存、校验和清理统一使用 POSIX 清单路径。已重新物化本工作区 23 个只发生过 CRLF 转换的文件，逐字节与索引核对，原有清单 SHA 保留。
- 本地素材库拒绝大小写冲突的租户名及重定向目录。索引有有界读取和版本缓存。Studio 每页显示 12 张，使用最长边 320 px 的缩略图和私有 ETag 重验证，导入绑定选中时的 SHA。事务内去重，工程回执和 ZIP 保留来源、授权和源 SHA。重新导出了 OpenAPI。样例宿主机渲染命令已停用，工程走隔离 Worker。
- Windows `scripts/check.py` 通过 Ruff，完整 FFmpeg 配置下后端 335 通过、10 失败。剩余涉及 ZIP 测试样本、符号链接权限及依赖 POSIX 进程组和信号的测试。素材及存储专项 15 通过，包含 5 项本地素材库测试。单独执行的视觉、空间及创作合约、TypeScript、生产构建、`npm run format:check` 和 `git diff --check` 全部通过。Prettier 配置接受现有 Windows 工作区的换行形式，Git 对精选包继续保持原始字节。
- 固定审查素材样例真实构建、连续预览、完整渲染和解码成功。输出 16 秒、480 帧、1080p30 无声样片，14 项素材与四个包均通过像素变化检查。最终工程源哈希为 `9157d104703e7c3521764af1ea694589dbdeef109ee005bae5e754936754c04c`。证据在 `docs/verification-material-packs.json`。此检查使用仓库固定样例和本机完整 FFmpeg，不代表原生生成代码可在宿主机运行。
- 真实原生模型、目标隔离部署、专业语音及完整人工试听仍待验收。

## 当前工作区复查 · 2026-11-24

以 `7991989` 和当前工作区的本地素材库、视觉模板改动为基线。复查记录对应本机 Windows，产品代码未改动。

- `scripts/check.py` 在当前工作区完成 Ruff，后端为 279 通过、63 失败。另建保留 Git 原始 LF 字节的验证副本，叠加当前项目文件并启用 UTF-8，后端为 328 通过、14 失败。Windows 自动转换换行会改变精选包字节并让能力目录返回 500。剩余失败包括精选包相对路径分隔符、Windows 子进程清理、POSIX 测试脚本、符号链接权限、`ffprobe` 缺失和 ZIP 测试样本的路径转换。
- 当前工作区的本地素材库原有 2 项测试通过。隔离的 3 项诊断分别复现 Windows 下大小写不同的租户别名、畸形索引未处理异常和并发导入同一素材得到两个项目图片 ID。预先存在同哈希存储对象时仍可复现重复目录项。
- 默认 Studio 端口已被占用。保留原服务，在验证副本配置 Chromium 和独立端口执行原有 20 项浏览器流程，19 通过、1 失败。失败用例的 trace 显示输入新封面标题后，两个旧版本 GET 在提交前完成，fork 请求携带旧标题并返回 202，新版本保留了旧值。后台版本刷新需要和编辑器本地草稿分离。
- 视觉、空间和创作合约检查及 TypeScript 通过。Studio 生产构建通过，主包 672.34 kB，空间包 890.66 kB，均为压缩前的构建产物大小。原始 LF 副本的 Prettier 检查和当前工作区的 `git diff --check` 通过。Windows CRLF 工作区的默认 Prettier 检查报告 30 个文件。
- 静态检查发现新本地图的来源和授权未进入交付包的 `generated-assets.json`，已签出的 OpenAPI 也缺少本地素材接口。视觉模板的 `render-previews.mjs` 直接从命令行接收工程及输出路径并在宿主机打包执行，未运行该脚本。原生模型、隔离部署、真实配音、素材挂载和全片人工验收未执行。

## 混合本地素材库 · 2026-11-24

- 新增外部可配置、按租户分隔的 PNG 索引和登记 CLI。创作页可选本地图片；创建项目后经所有权校验、源哈希核对和既有规范化图片链路导入，保留来源、授权、本地 ID 和源 SHA。重复导入返回已有项目图片；外部目录不挂载给生成代码或渲染器。
- 新增 API/CLI 测试 2 项通过，覆盖真实 PNG 登记、预览、租户与项目隔离、重复导入、哈希篡改拒绝和伪造路径拒绝。`npm run build` 通过；`npm run typecheck` 通过。
- `.venv\\Scripts\\python.exe scripts/check.py` 在本机 UTF-8 环境下基础检查通过，后续全量后端测试 46 failed / 296 passed（与本次增加 2 项前的 46 failed / 294 passed 相同失败数）；未将全量测试标为通过。配置 Chrome 后 `npm run test:ui` 被已占用的 127.0.0.1:5173 端口阻止，测试未启动。
- 尚未配置真实外部素材目录或隔离部署挂载；本版只接入 PNG。新主题 Agent 选材质量、完整渲染与人工试听仍待部署验收。

## AI Agent 视觉模板 HTML 优化 · 2026-11-24

- `examples/agent-video-templates/index.html` 增加六类可编辑场景、16:9 / 1:1 / 9:16 布局预览、字幕规范和 150 帧动效时间轴；保留两套独立风格与 SVG 素材。提供包含 HTML/CSS/JS、设计包和本地字体的 ZIP。
- 本地 Chrome Headless Shell 检查：两套切换、SVG 加载、文案编辑、竖屏切换、时间轴和 390 px 宽度无横向溢出均正常；无页面脚本错误。
- `.venv\\Scripts\\python.exe scripts/check.py`：基础检查通过，后续 63 failed / 277 passed；设 `PYTHONUTF8=1` 重试为 46 failed / 294 passed。一个已复现失败为 Windows 默认 GBK 读取素材清单时的 `UnicodeDecodeError`；其余全量失败未归因于本次静态页面。
- 配置 Chrome 后执行 `npm run test:ui`：Playwright 启动前因 `127.0.0.1:5173` 已被占用退出，未得到 UI 测试结果。以上不作为项目全量验收通过的证据。
- 补齐深青/暖白各六枚图标与三个可点播动效入口。修复本地 `file://` 下外部 SVG `<use>` 不显示的问题，页面预览改用内嵌路径，保留可下载的矢量源文件。浏览器验证帧 20/70 的元素可见状态不同、一键播放推进帧数、两套各六枚图标可见且无脚本错误。

Date: 2026-10-30. Baseline: V2.1 source restored from the delivered archive.

## Scope and acceptance
- Replace the new-product creation flow with engineering-mode planning, real TSX generation, compiler/render observations, bounded repairs and visual review.
- Retain explicit legacy/template compatibility. Do not call native inference verified without credentials and infrastructure.
- Add standalone generated project delivery, trustworthy font handling, professional Qwen policy, and API/UI progress.
- Maintain all 54 baseline backend tests and four browser tests; add meaningful state-gate, security, repair, build and export checks.
- Provide AGENTS.md, Roadmap.md, README.md, architecture, contracts, operation and acceptance documentation.

## Constraints
No Docker or native provider credentials are available in this execution environment. Never bypass this by running uploaded/generated model code on host. Authored trusted fixtures may validate compiler/render tools independently, with that distinction recorded.

## Progress
- Source restored; dependencies installed.
- Core implementation in progress.


## Delivery — 2026-10-30
- Added typed production planning, native engineering actions, real TSX file tool, isolated compiler/render tool, source-hash gates, keyframe/image checks, accepted-source resume, state/asset persistence and full project export.
- Added /api/v3/videos with engineering/Codex/professional defaults; retained v1 template compatibility and all baseline tests. UI displays actual project images/video rather than evaluating generated code.
- Professional mode resolves Qwen and requires real alignment; unknown legacy voice caches are not accepted as Qwen. Required font failures now stop rendering.
- Added AGENTS.md, Roadmap.md, README.md, architecture/domain/contracts/authoring/operations documents and real-deployment acceptance script.

### Executed validation
- `.venv/bin/python scripts/check.py`: Ruff clean; 82 backend tests passed; TypeScript passed including independent engineering template; Vite production build passed.
- `CHROME_EXECUTABLE=/tmp/video-agent-chromium npm run test:ui`: 5 passed, including explicit legacy flows and engineering default request.
- `npm run format:check`: passed.
- `scripts/verify_engineering_fixture.py`: actual TypeScript error observed, source repaired, Remotion build/keyframes/final rendering passed, 600 frames and full decode passed. This used fixed authored decisions, not native inference. Approved earlier Qwen audio reused, not newly synthesized.
- `scripts/verify_engineering_pipeline_fixture.py`: full pipeline/storage/export passed; seven state commits, nine keyframe assets, complete source and nested project export verified. Silent draft fixture.
- Assistant inspected three rendered keyframes for Chinese glyphs/layout/captions. This is not user or professional acceptance.

### Remaining deployment acceptance
No Docker daemon/gVisor or provider credentials in this environment. Real native-to-video inference, code container isolation, professional audio/listening quality and cross-Worker fault recovery require target-environment acceptance. No fixture result is labelled real native inference. Existing SSO/RBAC/billing and arbitrary project runtime support are not claimed.


## V4 follow-up (2026-11-16)

Implementation and fresh checks are recorded in `goals/2026-11-16-visual-explainer-v4.md` and `docs/verification-v4.json`; historical V3 fixture results above are unchanged.

Self-project narrated 4K follow-up: see `docs/verification-project-intro.json` and the final section of `goals/2026-11-16-visual-explainer-v4.md`. This extends actual media verification, not native-model or isolation acceptance.

Material/bookend follow-up: see `docs/design/material-library-and-speech-cn.md` and `docs/verification-bookends.json`; actual Ming inference is not claimed.

## 2026-11-17 creator publication follow-up

Added audience/intent editorial contracts, independently rendered publication thumbnail,
readable first-frame opening, topic-driven closing and hash-bound content review. Both
render paths and editable exports updated. Evidence is in goals/2026-11-17-creator-production.md
and docs/verification-creator.json; real native/TTS/isolation acceptance remains separate.

## 2026-11-18 content strategy follow-up

Added four independent editorial dimensions and six purposes; new native creator plans
resolve a scene-linked strategy and receive purpose-specific review. Existing execution,
evidence, voice and hash gates remain. See goals/2026-11-18-content-taxonomy.md and
verification-taxonomy.json for the exact implementation and measured checks.

### Review follow-up · 2026-11-18
Moved complete engineering plan and typed-action validation into bounded native retries;
rejected conflicting editorial duplicates and prevented stale title/language/mode boards.
159 backend / 9 browser flows, TypeScript/build and six authored strategy checks passed.
See goals/2026-11-18-content-taxonomy.md for scope, safe feedback and deployment limits.

## 2026-11-18 — concrete objects and causal motion

Added an optional data-only object stage, eleven recognizable vector actors, named ports,
physical/wireless connections, distinct video/audio/control/data flows, power/play/volume
state, measured narration anchors and three original opt-in quiet Foley cues. Integrated
Studio editing, semantic planning guidance, protected native composition/review, schemas,
font/asset/export handling and README/design documentation. No keyword topic routing.

Validation: scripts/check.py passed (183 backend tests, three TypeScript checks, Vite build);
configured npm run test:ui passed all 10 browser flows; format and six authored taxonomy
contracts passed. verify_object_scenes.py built/rendered both paths (9s/1080p), observed
screen RGB changes and all three cues at -26.66 dBFS; creator fixture also rendered both
paths and a separate 4K thumbnail. Source/props/asset hash gates remain enforced.

HDMI was reauthored with eight object/action scenes and unchanged actual Edge narration /
WordBoundary timings. Both 121.1s/3633-frame 1080p and native-vector 4K videos decoded;
14 encoded frame samples and an actual continuous connection clip were reviewed. See
verification-object-scenes.json and verification-hdmi-object-scenes.json. Illustrations,
not hardware/HDR/120Hz measurement; no real native inference or full human listening
certification. Arbitrary photo/3D generation and unknown-subject quality remain open.


## 2026-11-18 semantic production increment

Implemented typed AI information/state scenes, twelve shared semantic components, local
device-screen binding, structured shot intents, mediated original SVG/PNG assets and
receipts/recovery/invalidation. Added per-event causal windows, exact expectation review,
Studio editing and source/asset dependency evidence. README, architecture, contracts,
authoring guide, user/API docs and Roadmap now describe implemented and remaining scope.

Routine verification: 208 backend tests, Ruff, three TypeScript projects, production build,
all 11 configured browser flows, format checks and six editorial contracts passed. See
goals/2026-11-18-semantic-scenes.md and docs/verification-semantic-scenes.json for fixed
render evidence and limitations. RenderPlan keys are not a rendered-scene cache; image/3D
services and deployed native unseen-topic acceptance remain open.


## 2026-11-18 semantic review follow-up

Rechecked deployment/recovery/preview contracts and fixed the render image's missing local
runtime module, canonical asset cache recovery and whole-batch validation, identical-request
gate preservation, global presentation/runtime dependency hashes, and probed clip metadata
matching its declared frame range. Receipt bytes stay bounded at 128 KiB.

Verification: 224 backend tests, Ruff, three TypeScript projects, production build, all
11 configured browser flows, format and six editorial checks passed. Details and media
evidence are in goals/2026-11-18-semantic-review.md. Docker is absent; structural image
packaging verification is not an actual isolated image build/run or native inference test.

## Project-owned illustrated production follow-up

Executed scripts/check.py: Ruff, 244 backend tests, all TypeScript projects and Studio build
passed. Configured npm run test:ui: 12 passed. npm run format:check and git diff --check passed.
The protected Remotion fixture rendered/decode-checked 2127 frames at 1080p with authenticated
project imports and actual reused Edge timing. It did not invoke native/image inference.
Actual provider/isolation deployment remains unconfigured; no host fallback was added.
See goals/2026-11-18-production-assets.md and docs/verification-production-assets.json.

## Reference-production correction evidence

Final source checks: 256 backend tests, 13 browser flows, pure code/theme/parameter/flow
invariants, TypeScript/build/format passed. Fixed reviewed source rendered 480 frames/16s
at 1080p with silent estimated timing and real theme comparison. Asset/global identity,
full code pages, measured tail budgets and binding review integrate the prior semantic/image
work toward main. Actual native/image providers and Docker/gVisor remain deployment work.
See goals/2026-11-18-reference-optimization.md and docs/verification-reference-corrections.json.

## Spatial storytelling · 2026-11-23

Implemented protected Three city/camera, registered-image matrices, stable network layouts
and shortest-hop propagation, neon_horizon and complete API/TS/catalog/editor integration.
Final scripts/check.py passed: 268 backend tests, pure visual/spatial contracts, TypeScript
and Studio build; 14 configured browser tests and format/diff checks passed. Fixed reviewed
platform dispatcher rendered and decode-checked 840 frames/28 seconds at 1080p30, with four
continuous previews, three actually consumed original stills, distinct state frames and matching
final source hashes. Exported editable project. See goals/2026-11-23-spatial-storytelling.md
and docs/verification-spatial-scenes.json. The sample is silent/estimated, not actual native,
image/TTS inference, Docker/gVisor deployment or human complete playback/listening certification.

## Content-driven creation · 2026-11-23

Following the clarification that creativity belongs to the engineering Agent, implemented
per-scene free creative contracts, source artwork bindings/manifests, custom measured causal
events and review, general Three activation and Studio design inspection. New native planning
requires the contract; historical plans remain loadable. Final checks: 288 backend tests,
15 browser flows, pure render/timing contracts, TypeScript/build/format passed. The actual
new-topic deployment preflight is blocked by missing Docker/provider configuration/credentials;
no native creative generation or new generated-code render is claimed. See
goals/2026-11-23-creative-production.md and docs/verification-creative-production.json.

## Curated material packs · 2026-11-23

Implemented4 pinned packs/14 new materials, Studio/native discovery with real previews,
selective protected source staging, PNG/embedded-GLB receipts, capture readiness, full
hash invalidation/recovery and licensed source export. Fixed still capture before async
models drew; added object-region assertions. See goals/2026-11-23-material-packs.md,
docs/design/material-packs.md and verification-material-packs.json.

Verification:306 backend tests,16 UI flows, pure contracts, TypeScript/build, format and
fixed16s/480-frame1080p30 compile/preview/render/export regression. Silent fixed fixture;
native unseen-topic selection/creation, Docker/gVisor and professional listening remain
separate deployment acceptance. No arbitrary generated-source host execution added.

## Material pack review · 2026-11-24

Fixed checkpoint selection/identity, preflight staging, strict GLB ranges, browser errors and
repeated scans; strengthened model cleanup/draw/4K handling.8 pre-fix failures were reproduced.
Final316 backend tests,17 UI flows, contracts/types/build/format/diff and fixed16s real material
compile/preview/render/decode/export passed. See goals/2026-11-24-material-pack-review.md and
docs/design/material-pack-review-20261124.md. No native/deployment/human listening claim.

## Full project review · 2026-11-24

Fixed atomic cancellation/claim decisions, terminal worker fencing, retry quotas, failed-render
receipt precedence, session-owned Studio state, subprocess pipe deadlines and graceful cleanup,
atomic access-key publication, ZIP prefix collisions, common source credential redaction,
full narration edits/Qwen early limits and resumable SSE. Reduced capability polling; pinned
FastAPI0.136.3/Starlette1.10.0/python-multipart0.0.34 in API, lock and Qwen HTTP service.

340 backend tests and20 browser flows, contracts/types/build/format/dependency checks passed.
Fixed trusted compatibility pipeline rendered/decoded20s1080p30 and exported source; PARTIAL
with no voice and estimated timing. PGlite SQL/API checks passed, not native PostgreSQL
concurrency. Native/Docker/Temporal/professional voice/listening remain deployment acceptance.
See docs/design/project-code-review-20261124.md and docs/verification-project-review.json.
