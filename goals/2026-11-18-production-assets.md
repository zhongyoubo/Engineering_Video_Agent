# Project-owned visual production

## Scope and acceptance
Replace conversation-only image generation/manual compositing with mediated project tools:
configured image gateway, project-scoped raster imports, durable validated receipts, shared
layer rendering and narration-bound transforms. Preserve native source authoring and offline
isolated rendering. No host execution fallback for generated code; no fabricated inference.

Baseline: source 66bc92a; scripts/check.py passed (224 backend tests, TypeScript and Studio build).
Acceptance: scripts/check.py; configured test:ui; format:check; fixed trusted raster fixture
render with causal before/during/after samples. Gateway transport tests are simulated responses,
not deployed model acceptance. Actual native/provider/isolation requires configured services.

## Implementation
In progress. Documentation and execution evidence will be recorded after checks.

## Delivered

- Worker-owned eva-image-1 image gateway adapter, disabled until configured. No provider URL
  or secret enters native/generated-code containers. Bounded stream, actual PNG decoding,
  redirect/URL refusal, cutout transparency and metadata removal are enforced.
- Authenticated immutable project image catalog and Studio upload before job submission.
  Native planning sees actual bounded previews; resolver requires tenant AND project ownership.
- Request/inspect/recover/export integrates raster receipts with existing fenced checkpoints;
  replay restores retained bytes without re-inference. Old SVG receipt keys stay compatible.
- Shared registered illustration backgrounds, unframed artwork, per-shot colors and measured
  move/reveal/scale/rotate events reuse existing causal review and exact-source gates.
- Real deployment acceptance script requires native job success, actual gateway receipts,
  a transparent cutout and measured transforms. Fixed source/storyboard verifier remains separate.
- Updated README, Roadmap, design/authoring/AGENTS, API schemas and progress/earlier goals.

## Executed verification

- `.venv/bin/python scripts/check.py`: passed; Ruff, **244 backend tests**, three TypeScript
  projects and Studio build. Existing botocore deprecation and Vite chunk-size notices remain.
- Configured `npm run test:ui`: **12 passed**, including actual project-image upload before
  native job submission and explicit unconfigured-native failure (no model inference claimed).
- `npm run format:check`, `git diff --check`: passed.
- Both new verifier scripts: Ruff passed. Dedicated raster tests include real normalization,
  APNG/geometry/stream budgets, corrupt recovery, secret-safe transport errors, cancellation,
  repeated requests, revision keys, old SVG recovery and cross-project/tenant refusal.
- `CHROME_EXECUTABLE=<downloaded Chrome Headless Shell> .venv/bin/python
  scripts/verify_production_assets.py --media-directory <hash-pinned dinner-media>`: passed.
  **70.9s, 2127 frames, 1920×1080/30fps**, all-frame decode passed; 8 authenticated imports;
  three measured causal transform differences; continuous clip metadata validated; full
  editable Remotion project exported. Sources and existing real Edge audio were reused.
  See docs/verification-production-assets.json for exact source/media hashes and preview counts.
- System Chromium initially failed before launch due to socket permissions. Installing and
  selecting Chrome Headless Shell resolved this environment issue; no test was skipped.
- `verify_image_production_deployment.py --provider codex --voice edge`: exits at explicit
  preflight because Docker, native provider configuration and the image gateway are absent.
  This is a blocked deployment acceptance, not a successful integration test.

## Limits

A gateway service/model must implement the documented project protocol; it is not bundled.
The conversation image tool is not treated as an application integration. Actual image/native
inference, Docker/gVisor deployment, unseen-topic quality and full human viewing/listening
remain unverified. Configured availability is not service health or professional quality.
No standalone FFmpeg compositor was promoted to a hidden fallback; shared Remotion remains
responsible for preview/final/source delivery. Broader 3D/video/camera/cache work remains open.
