# Engineering video Agent implementation

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
