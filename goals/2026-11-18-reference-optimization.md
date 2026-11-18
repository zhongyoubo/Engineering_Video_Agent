# Reference-production corrections

Scope: integrate latest feature work toward main; prevent cross-shot asset collisions;
replace code truncation with bounded visible pages and source-line bindings; budget measured
motion before rendering; propagate shared theme tokens; strengthen asset-consumption review;
add composable parameter-driven mechanisms and actual fixed-source rendering evidence.

Baseline: c9664c7, 244 backend tests passed. Preserve existing tests, isolation, tenant/fence
checks, real timing and exact-source gates. Generated code never runs on host. Fixed reviewed
verification source only may host-render. Native/image deployment remains unavailable.

Acceptance: scripts/check.py, configured test:ui, format:check, meaningful defect regressions,
and fixed actual Remotion render showing changed mechanisms/code pages/themes. Record actual
results and remaining deployment limits here. No fabricated provider or listening acceptance.

## Delivered

- Global asset ID validation across shots, declaration completeness, native request checks,
  and build rejection for recovered materials that no longer match the current plan/bytes.
- Full code wrapping/pages and original source-line focus, replacing 14-line/68-character
  silent slicing. Large focused ranges progress through pages; source line bounds are checked.
- Actual word-boundary event endings now contribute to frame allocation and held result frames.
  Strict exact/max/locked constraints remain strict; impossible plans fail explicitly.
- Protected shared theme, viewport and mechanism modules; captions/panels/stage/thumbnail and
  editor fallback reuse theme tokens. Existing image colors and intrinsic device colors stay factual.
- Five composable numeric mechanism entities with parameter events; dial/tree/metric linkage,
  reservoir/queue rate integration, capacity, processed count and overflow; Studio edits persist.
- Asset usage/binding review and deployment consumption checks reject unused/hidden/unrelated
  generated receipts, require distinct generated image hashes/background/animated cutout.
- README, roadmap, architecture, authoring, schemas, catalog, CI evidence and earlier goals updated.
- Main-targeted integration includes the prior semantic/image work; main is unchanged until merge.

## Executed acceptance

- Baseline: **244 backend tests** passed.
- Final `.venv/bin/python scripts/check.py`: Ruff, **256 backend tests**, real pure rendering
  contracts, three TypeScript projects and Studio production build passed.
- Configured `npm run test:ui`: **13 passed**, including actual SVG state update when changing
  a shared parameter and persistence across revision saves.
- `npm run format:check`, `git diff --check`: passed. Existing botocore deprecation and Vite
  chunk-size notices remain; no test was skipped or weakened. The catalog's exact expected
  count was increased from 30 to 31 and new entry/source assertions added for the new capability.
- Fixed-source `verify_reference_mechanisms.py`: **16 seconds / 480 frames / 1080p**, full
  decoding and continuous clip metadata passed; two themes differ in real pixels. Actual sampled
  review confirmed the final source line 24 and its issue highlight are visible on page two.
  This fixture is silent and explicitly estimated, not measured new narration or native inference.
- The fixed verifier was run again after protected source changes; a rerun-only node_modules
  symlink error was corrected, and the final complete rerun passed. Source/video hashes and
  theme comparison are in docs/verification-reference-corrections.json.
- Deployment acceptance script stops at explicit preflight because Docker/gVisor and real
  native/image provider configuration are absent. This is not recorded as a passing integration.

## Limits

The implemented primitives form a first reusable parameter/rate vocabulary, not the entirety
of every reference video. Calendars, richer charts, arbitrary paths/morphs/cameras, generated
art reference conditioning, independent occlusion/OCR and human full playback/listening remain.
Tail-budget extension repairs the reproduced measured-word case; contradictory state/dependency
plans and impossible strict timings do not have an unrestricted automatic replanner. Native
visual material review supplements structural checks, not an independent pixel proof for
arbitrary authored TSX. No generated/user code host fallback was added.
