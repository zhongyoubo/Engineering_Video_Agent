# Semantic visual production implementation

Baseline: main fcf4437 plus unmerged object-scenes dce4a25 (PR #4). Work is isolated
on feat/semantic-scenes-20261118; no changes to the user's existing checkout.

Scope: typed semantic entities, measured state transitions and causal expectations;
structured shot intents; device-screen bindings and shared trusted renderer; mediated
original SVG asset production and durable asset receipts; event coverage/review;
Studio editing, schemas, fixtures and README/design/roadmap evidence.
Keep native authoring, isolation, tenant scope, lease cancellation and exact-hash gates.
No keyword topic routing, host execution of generated TSX, invented native inference,
or claim that image/3D services or arbitrary unknown-subject quality are verified.

Acceptance: existing backend baseline; scripts/check.py; format and configured Chrome
browser flows; fixed Agent and RAG data through both real render paths; readable screen
binding after device movement; last causal event and before/after result coverage;
asset idempotency/recovery and stale-source review rejection. Record actual results.

Progress: implementation and fixed render/browser verification completed; see results below.

## Implementation

Added data-only semantic contracts, structured shot intent and twelve AI visual treatments;
shared standalone/device-screen renderer; measured causal compilation and atomic failure
clearing; explicit expectations; mediated bounded SVG/PNG creation with source/font hashes,
font license, companion images, recovery and invalidation. Added Studio edit/save/reload,
all-clip display, RenderPlan dependency keys, exported schemas and V5 status mapping.

## Executed checks

- Baseline: 183 backend tests passed before implementation.
- `.venv/bin/python scripts/check.py`: 208 tests passed, Ruff clean, all three TypeScript
  projects and Vite production build passed. Five existing dependency warnings; existing
  Vite bundle-size warning remains.
- Configured `CHROME_EXECUTABLE=... npm run test:ui`: all 11 flows passed, including actual
  screen bounds, shared state, semantic edit/save/reload and capability truth.
- `npm run format:check`: passed. `scripts/verify_content_taxonomy.py`: six fixed contracts passed.
- Added regressions for invalid graphs/bindings/state/timing, late result bounds, controlled
  asset recovery/dedup/cancellation/tenant scope, protected sources, exact semantic review,
  stale-source rejection and failed compilation clearing.

## Limits

This environment has no deployed native provider/container credentials. Fixed repository
fixtures are the only TSX executed by explicit verification scripts; generated or uploaded
TSX still requires the offline isolated production worker. No native inference, actual
business execution, new TTS generation or full human listening is claimed. Image/video/3D
services, arbitrary layer graphs, general FFmpeg media composition, scene-video caching
and unseen-topic quality remain on Roadmap.md.

## Actual render evidence

`CHROME_EXECUTABLE=... .venv/bin/python scripts/verify_semantic_scenes.py` passed.
The fixed five-scene Agent/RAG/gallery fixture produced both 1920x1080 and native
3840x2160 outputs: 20 seconds, 600 frames, full decode passed. Nine continuous windows
include before/during/after states and late human confirmation. Rendered samples show
updated tool-result rows, bound device status and answer/source changes; actual center
ROI RGB differences were [8.46, 6.67, 5.91]. Final encoded samples were visually inspected;
this is sample review, not full playback/listening.

`verify_object_scenes.py` passed both 9-second/270-frame paths, eleven object shapes,
actual screen color differences and quiet Foley (-26.66 dBFS peak).
`verify_creator_publication.py` passed both 6-second/180-frame paths and separate
3840x2160 thumbnail rendering. Evidence JSON records the final source/renderer hashes.

Submission is a stacked change over unmerged PR #4. Merge that dependency first, then
retarget the semantic PR to main. No main-branch merge is claimed.
