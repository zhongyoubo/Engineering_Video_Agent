# Curated material packs

## Scope and baseline

Implement style/subject/affordance discovery, pinned reviewed material packs, selective
offline workspace staging, image/model receipts and source/asset preview/review/export.
Integrate a bounded first collection of licensed upstream vector art, raster 3D-style art,
adapted Remotion motion components and an embedded GLB model. No bulk dependency upgrade,
topic keyword router, arbitrary pack upload or model-source execution on the application host.

Baseline d989b5e: scripts/check.py passed (288 backend tests, pure contracts, TypeScript/build).
Model credentials and Docker remain absent; no native creative-quality claim.

## Acceptance

- scripts/check.py, configured test:ui, format/diff checks; preserve baseline assertions.
- New manifests verify every file/hash, provenance/license, parameters and previews.
- Only selected code packs enter protected src/vendor; binary assets are requested by a
  canonical versioned library reference and go through bounded validated receipts.
- Recovery, stale-byte rejection, all dependency hashing, tenant-safe project integration,
  source invalidation, native binding review and standalone exports remain intact.
- Actual fixed platform integration preview compiles/renders selected assets/components;
  fixed verification never accepts arbitrary uploaded/model source/path arguments.

## Progress

- Audited existing material registry, asset routes, creative contracts and recursive hashing gap.
- Pinned upstream revisions selected; license and media inspection in progress.

## Implementation

- 4 hash-pinned licensed curated packs / 14 entries (8 SVG, 3 PNG, 2 motion components,
  1 self-contained GLB); legacy 34 entries retained for total 48. Real raster previews,
  parameter/style/subject/affordance discovery and Studio browsing/filters.
- Native planning/authoring sees a bounded actual preview sheet; new typed search/select
  actions and automatic planned-material staging. Only selected modules/dependencies enter
  protected src/vendor. No arbitrary asset/source downloads or runtime npm installation.
- Canonical PNG and bounded embedded GLB receipts, consistent cache/recovery, byte/privacy
  checks, source/asset bindings, licensed standalone export and recursive dependency hashing.
- Fixed rendering exposed asynchronous GLB still capture before the model drew. Repaired
  commit/draw readiness and preserved the WebGL buffer. Added explicit per-model-region
  nonempty still checks so unrelated changing text cannot mask a blank object.
- README, Roadmap, AGENTS, design/authoring/template docs, third-party notices and generated
  API/domain/Agent schemas updated. Runtime image/source budgets and isolation boundaries
  remain enforced.

## Checks

- scripts/check.py passed: Ruff, 306 backend tests (baseline288 +18 new), protected visual,
  spatial and creative invariants, TypeScript projects, production Studio build.
- Configured npm run test:ui: 16 passed, including actual authenticated PNG previews,
  filtering by style/type, resolution restrictions, empty search and all15 existing flows.
- npm run format:check and verifier-specific Ruff passed. git diff --check passed.
- Fixed verify_material_packs.py compiles and renders all14 entries across4 scenes, checks
  current source fingerprints, per-model still visibility, actual continuous previews,
  480-frame/16s1080p30 final decode, pixel changes and a licensed standalone source ZIP.
  Exact executed source/media hashes are in docs/verification-material-packs.json.

## Limits

This is a curated subset, not entire upstream libraries. PNG stays2D and retains its real
pixel limits; the optimized model uses512px textures. Actual native-provider selection and
new-topic creation require the configured isolated Worker and credentials, absent here.
No new image/native/TTS inference or professional voice/listening acceptance is claimed.
The visual sample is fixed reviewed platform source, silent estimated draft timing.

## Windows portability follow-up · 2026-11-24

Git now preserves the pinned pack bytes. Staging, pruning and verification use canonical
POSIX relative paths on Windows as well as Linux. On Windows the material and raster
regression group had 51 passes and two failures at symbolic-link creation (`WinError 1314`).
The pre-fix Windows staging and recovery failures passed after the path correction.
The configured Chromium suite passed all 20 flows. See the main engineering goal for the
complete checks and deployment limits.
The reviewed fixed fixture also built, previewed and rendered 480 frames at 1080p30 using
the locally installed full FFmpeg. All four scene groups showed measured pixel changes.
Its source hash and media result are in docs/verification-material-packs.json.
