# Visual explainer V4 implementation

## Scope and invariants

Upgrade the existing engineering path: output profiles, voice identity/cache, semantic motion specifications, reusable visual primitives, continuous preview artifacts, waveform/timeline inspection, MCP access and accurate documentation. Preserve v1 compatibility, credential-free rendering, source-hash gates, cancellation, fencing and all existing tests. Do not claim real provider inference or human-certified quality from fixtures.

## Baseline (2026-11-16)

- Source: `4d46238d08dfd84ae751cb370b89fa62b9059a44`.
- Python 3.12, locked requirements; Node/npm dependencies installed.
- `pytest apps/api/tests -q`: **82 passed**.
- `npm run typecheck` and `npm run build`: passed.
- Browser test first attempted before Python installation completed: startup failed. Repeated after installation: Chromium aborted on environment socket/ptrace restrictions before assertions; no browser pass claimed.
- No Docker daemon, supplier credentials or speech weights configured. Native inference and isolation deployment acceptance remain blocked; trusted authored render fixtures are separate evidence.

## Work and final verification

Updated below with actual commands, results and remaining deployment checks before submission.

## Implemented

- RenderProfile drives 1080p/4K across domain, compositions, preview validation, media checks and Studio.
- VoiceSpec, effective provider configuration and cache invalidation; speed applied before alignment; silent professional audio rejected.
- Semantic SceneSpec/anchors/events, seven deterministic visual patterns, two design packs, protected motion kit and standalone export.
- Continuous per-scene MP4 previews, sampled motion sheets, current-hash review requirements and durable clip assets.
- Actual PCM waveform/peak/RMS, motion editor, save/fork, same-tenant revision comparison.
- Optional official-SDK stdio MCP with seven tools reusing authenticated API jobs; idempotent submissions and optimistic revision forks.
- Runtime insertion/effective plan synchronization; regenerated schemas; implementation/target documents; GitHub CI definition.

## Actual final checks

- `.venv/bin/python scripts/check.py`: ruff passed; **92 backend tests passed**; TypeScript and production build passed. Original 82 tests retained.
- `CHROME_EXECUTABLE=<compatible Chromium wrapper> npm run test:ui`: **6 passed**, including all 5 original tests and new 4K/motion/fork coverage. System Chromium failed to start; compatible headless Chromium 138 worked after removing single-process mode.
- `npm run format:check`: passed.
- `scripts/verify_visual_v4.py`: real compiler, 9 full-resolution keyframes, 3 continuous clips, 3 sampled motion sheets; **3840x2160, 30fps, 270 frames, 9.0s**, full decode passed. Exact current renderer/Root/motion-kit/fixture source checked. Silent authored fixture, not native generation or TTS.
- Existing `scripts/verify_engineering_pipeline_fixture.py`: real compiler-error/repair/render/persistence/export path passed (7 persisted steps); updated for motion preview artifacts. Programmed fixture review, no model inference.
- Optional SDK `scripts/verify_mcp.py`: real stdio initialization/tool discovery, authenticated HTTP calls, duplicate submission deduplication, revision fork and cancellation passed.
- Sample scene images visually inspected by assistant; complete human playback/listening not certified.

## Remaining target-environment acceptance

No Docker daemon, provider API keys or speech weights are available here. Real Codex/Claude inference, newly synthesized natural Mandarin male narration, gVisor/isolated 4K performance, independent review quality, target PostgreSQL/S3 and real inference cancellation remain unverified. A bounded motion window is not full transition coverage; a lightweight anchor editor is not a full nonlinear editor. See docs/verification-v4.json.

The GitHub Actions workflow is newly added; local success does not assert a remote CI run passed.


## Three-reference review and self-project test (2026-11-16 follow-up)

- Re-examined all three local video references; documented similarities, pattern coverage, production/UI gaps and deployment boundaries in `docs/reference-review-and-self-test-cn.md`.
- Added fan overview layout, pattern cardinality/label bounds with matching native planning constraints, wrapped labels, actual Edge word-boundary streaming and optional dependency/proxy. Kept explicit forced alignment requirements and no implicit provider fallback.
- Fixed paused template preview showing an empty frame zero. Browser regression checks actual ancestor opacity and fan layout persistence.
- `.venv/bin/python scripts/check.py`: 95 backend tests, ruff, TypeScript and build passed; frontend build/format rechecked after UI fix. Latest backend recheck after planning-constraint refactor: 95 passed. Browser: 6 passed after adding preview regression. No test deleted or skipped.
- Real self-project UI ingestion: 187 files, 6 storyboard scenes, evidence browsing, motion edit, saved revision and comparison. Explicit template/storyboard mode, not model generation.
- New Edge Yunxi male audio: 7 segments, 57.858669 seconds, 132 measured word spans. Only exact already-public README excerpts were sent, after checking public repository visibility/provenance. No source upload or private text was sent. Not Qwen/Whisper verification.
- Fixed authored intro source: real compiler, 21 keyframes, 7 continuous clips/contact sheets, 3840x2160 / 30fps / 1927 frames / 64.235s H.264/AAC; full decode passed. Complete project fingerprint is recorded in `docs/verification-project-intro.json`; stale build/preview/final package gates enforced.
- Final muxed audio: -17.41 LUFS integrated, -4.46 dBTP true peak, 6.9 LU range. No full-black segment >=0.2s detected. These are measurements, not pronunciation/listening certification.
- CI diagnosed actual Ubuntu-latest/Playwright installation incompatibility and full-Chromium old-headless removal. Pinned Ubuntu24.04 and installed Remotion-compatible Headless Shell; preserved diagnostics. Code a36532f CI run43916631812 passed every step, including visual fixture and MCP.
- Editable project ZIP includes all media/font/source. UI capture is 1080p enlarged in a 4K composition; vector/text elements render at 4K. No claim that all raster source pixels are 4K.
- Remaining: actual Codex/Claude provider inference, Docker/gVisor isolation, full audio/video listening, advanced metaphors/object transitions, and complete persistent risk/readiness management. Existing target-environment boundaries remain.


## Material library and independent bookends follow-up

- Confirmed previous body uses Edge Yunxi, not Qwen or Ming; no reference-video frames, graphics or narration were extracted. Visual style was interpreted into repository-authored React/SVG; project UI is an actual recording; Noto retains its external font notice.
- Added reusable CoverScene/EndScene to protected motion-kit; authored and actually rendered independent 3s/4s 4K pages. Compiled assembly previews include first and final frames. Existing body retained by recorded video SHA, not falsely claimed as newly generated.
- `scripts/verify_project_bookends.py`: 210 newly rendered frames + 1927 verified reused body frames; final 2137 frames / 3840x2160 / 30fps / 71.233333s, full decode passed. Four body samples, including the intentional end fade, match source pixels with RGB RMS=0. Image content checks remain unchanged for content frames; the known transition is checked against the original source pixels. Measurements and hashes in docs/verification-bookends.json.
- New read-only 15-item catalogue has version/source/provenance/rights/readiness/hash; authenticated API and Studio browsing. Native planning receives the catalogue and validates versioned shot asset references; no keyword router or arbitrary source loader added.
- Ming adapter forwards configured reference audio/text and seed; hashes reference identity into only the Ming cache. Existing Edge/Qwen cache configuration is unchanged. Actual HTTP/PCM test is explicitly a fixture, not inference. Official Ming and SGLang sources checked; undocumented SDK control fields are not sent to the compatibility endpoint.
- Full check: 105 backend tests, Ruff, TypeScript and frontend build passed; 6 browser tests passed including material browsing. Formatting passed. No test was deleted/skipped or existing content threshold relaxed.
- No Ming endpoint, Qwen service, alignment weights or GPU CLI is configured; new video retains existing Edge speech. Naturalness, pronunciation and voice comparison remain unverified. Documented a same-script audition and separate oral-script/term/phrasing work before replacing the narration.

## 2026-11-17 publication follow-up

Creator presentation removes permanent tool/verification banners. Protected bookends are
topic-driven; preview adds the separate thumbnail and opening/final boundary samples.
Existing motion review and project-hash invalidation are preserved. See creator-production
implementation and fixed-render evidence; these samples do not establish full listening.

## 2026-11-18 content-purpose follow-up

Expanded creator/editor contracts without changing protected visual execution behavior.
The fixed creator fixture was recompiled and rendered for both paths, including separate
4K thumbnail and first/closing samples. New purpose metadata does not become an on-screen
badge. Structural six-genre samples remain distinct from native inference quality.

### Review follow-up · 2026-11-18
Fixed pending-target UI using obsolete strategy details, plus plan/revision consistency
and bounded native validation retries. 159 backend / 9 browser flows and build passed;
no new renderer, media or real native-quality acceptance claimed. Details:
goals/2026-11-18-content-taxonomy.md.
