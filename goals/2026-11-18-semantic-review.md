# Semantic production review and fixes

Date: 2026-11-18. Base: 9eae7ed (PR #5), preserving its unmerged PR #4 dependency.
Scope: recheck actual deployment inputs, asset recovery/idempotency, dependency evidence
and causal-preview receipts; directly fix reproducible failures without changing the native
isolation, provider, tenant/lease or exact-source acceptance boundaries.

## Findings and implementation

1. The image copied render.mjs without its new local import review-plan.mjs. It now copies
   both, and a regression checks transitive local runtime imports against Dockerfile COPY.
2. Recovery rewrote safe files but left unchecked SVG/PNG cache fields in state. Later
   deduplication could republish corrupt bytes. Entire receipts are now rebuilt canonically;
   the whole batch and budgets validate before writing; cached receipts check hashes/paths.
3. An identical asset request unconditionally cleared all gates. Exact unchanged workspace
   fingerprints now preserve acceptance; replacements, file repairs and partial I/O changes
   still invalidate all gates. Existing cancellation guards remain before publication.
4. Scene dependency keys omitted global theme/font props and root runtime modules. These
   now contribute to the digest; render_plan excludes itself, preserving stable refreshes.
5. Aggregate tool receipt limits did not reflect bounded multi-window lists. Receipts are
   capped at 128 KiB; continuous metadata must match integer scene bounds, probed dimensions,
   fps, actual frame count and duration. Existing count/size/causal gates remain enforced.

## Verification

New regression cases first exposed packaging, recovery, duplicate-request and presentation
hash failures. Added protocol checks cover invalid clip types/ranges/fps/count/duration,
missing video streams, bounded oversized receipts and post-publication I/O invalidation.

- `.venv/bin/python scripts/check.py`: Ruff, 224 backend tests, three TypeScript projects
  and production build passed. Existing five dependency warnings and Vite size warning remain.
- Configured `CHROME_EXECUTABLE=... npm run test:ui`: 11 passed.
- `npm run format:check`: passed; `verify_content_taxonomy.py`: six fixed contracts passed.
- Existing nine real semantic previews passed the stricter ffprobe/range validation.
- Fixed semantic renderer rerun: 20 seconds / 600 frames in both 1080p and native 4K;
  both full decodes passed, all nine real preview clips matched their declared ranges,
  and late human-confirmation coverage passed. Evidence is recorded in
  docs/verification-semantic-scenes.json. This was the fixed repository-authored fixture.

## Limits

Docker is unavailable here. The Dockerfile dependency regression and fixed repository-only
host render do not constitute an actual image build/run or native model inference acceptance.
Rebuild and execute deployment checks on the target isolated Worker. No user/model-generated
TSX was executed on host; no new TTS or human full-playback/listening claim is made.
