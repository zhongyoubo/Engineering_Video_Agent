# Spatial storytelling production

## Scope and baseline

Implement platform-owned SpatialCity, QuantityMatrix and NodeNetwork; measured semantic
parameters drive camera, quantity, layout and propagation. Add a dark stage, typed contracts,
protected source/dependency integration and an approximately 28-second fixed production sample.
Keep 30fps explicit; 60fps migration is not part of this increment.

Baseline: commit 202e1ba; scripts/check.py passed (256 backend tests, visual contracts,
TypeScript and production build). No Docker executable or provider/TTS configuration observed.

## Acceptance

- `.venv/bin/python scripts/check.py`: all checks pass; preserve baseline assertions.
- `npm run test:ui`: configured Chromium, existing flows and new spatial controls pass.
- `.venv/bin/python scripts/verify_spatial_scenes.py`: only fixed repository platform source
  and fixed typed data; actual build, continuous previews, 28s/840 frames/1080p decoding,
  current source/asset hashes and nontrivial frame changes.
- Same seed yields the same geometry; matrix counts stay bounded; network node identities
  and edge endpoints survive layout changes; propagation follows shortest graph hops.
- Native source cannot replace new protected modules; assets are registered, consumed,
  reviewed and included in exports. No network/assets/credentials in generated-code renderer.

The fixed platform render is not native inference, new image-model inference, a deployed
Docker/gVisor test or professional voice/listening acceptance. Do not fabricate these statuses.

## Progress

- Dependency compatibility checked: Remotion 4.0.538, React 19, R3F 9.4.0, Three 0.181.1.
- Implemented protected spatial state/render modules, standalone dependency locks, typed
  schemas, shared parameter/time/asset bindings, native guidance and catalog entries.
- Added neon_horizon consistently in domain, both TS props types, API capability discovery,
  material catalog and creation UI. Catalog now has 33 entries, with assertions for both additions.
- Fixed estimated start-edge motion budgets, software WebGL availability, asynchronous
  component commit/capture, final matrix tile settling and removal of nested still captions.
- `.venv/bin/python scripts/check.py`: passed, including **268 backend tests**, pure visual
  and spatial contracts, all TypeScript projects and Studio production build.
- Configured `npm run test:ui`: **14 passed** on final source, including selecting the new
  theme, verifying actual node position changes/48 identities/96 edges, and revision persistence.
- `npm run format:check`, separate verifier Ruff/Prettier checks and `git diff --check`: passed.
- Existing botocore deprecation and Vite bundle-size notices remain warnings. Spatial rendering
  is lazy-loaded; software WebGL throughput still depends on the deployment CPU/renderer.
- Final fixed media verification passed: **28s / 840 frames / 1920×1080 / 30fps**,
  actual build, four continuous causal previews, full MP4 decode, three registered consumed
  original city stills and nontrivial differences in all four shot pairs.
- Final project fingerprint: `295f646eae348b93f5bc8fbd73142f15f3de804e28002284fb84cb0535150f01`.
  Video SHA-256: `bfe185aa3b43deec13864192f35d18fc3b804eeded79d2064472add0bd6ebdf6`.
  Verified every protected source byte in the exported workspace equals the current template;
  contact sheet inspected for camera changes, settled 240 tiles, scattered IDs and propagation.
- Exported standalone project and verification JSON. No source/reference-media reuse, native
  inference, image inference, audio service, Docker deployment or human full-listening claim.
- Submission continues the existing main-integration PR #7 by fast-forward; no merge is performed.

## Delivery and remaining acceptance

Reusable mechanisms now pass through normal typed authoring, asset management, parameter
editing and renderer paths. The fixed sample is explicitly silent with estimated draft timing.
Configured native unseen-topic production, professional narrated alignment, isolation deployment,
general-purpose 3D modeling, 60fps and human playback/listening remain unverified. Pure frame
differences demonstrate motion, not semantic correctness of arbitrary future authored TSX.
