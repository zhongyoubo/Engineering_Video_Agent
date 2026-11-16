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
