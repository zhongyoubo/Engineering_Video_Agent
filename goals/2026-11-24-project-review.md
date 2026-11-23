# Full project review

Base f1f5ea5. Review API/auth, SQLite/PostgreSQL queue fencing, Temporal orchestration,
checkpoints, ingestion/runtime isolation, native driver, voice/timeline, media export/storage,
Studio session/edit state, reusable renderers and existing material fixes.

Baseline scripts/check.py:316 backend tests passed plus Ruff, visual/spatial/creative
contracts, TypeScript and Studio build. No Docker/native credentials or full professional
listening acceptance in this environment. Never run uploaded/model source on the host.

Acceptance: reproduce concrete bugs before fixes, add meaningful regressions, preserve all
baseline assertions, run full checks and configured UI flows. Record coverage and unverified
areas; no claim that passing checks prove the entire project bug-free.

## Confirmed findings

- Cancel/claim race; stale terminal workers can still pass guard/commit.
- Retry bypasses per-tenant active-job quota.
- Studio logout retains previous session's private state.
- Runner deadline ignores descendants after the parent exits; cleanup can block/leak children.
- First-start token publication races between processes.
- ZIP file/ancestor-directory collisions are accepted then fail during runtime materialization.

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

Pre-fix regression evidence:22 new backend cases failed across staged reproductions;
three browser regressions reproduced before correction. No baseline tests removed or weakened.
All24 new backend cases pass. Range test follows upstream safe full-response strategy.
Detailed findings, commands and next priorities are in the design review linked above.
