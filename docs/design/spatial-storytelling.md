# Spatial storytelling · 2026-11-23

## Purpose and implementation

The reference video uses camera perspective, repeated imagery, stable objects and causal
propagation to make quantities and relationships visible. This increment implements three
composable platform components rather than another topic-specific storyboard template.
Native authoring still chooses subjects, artwork, source and visual form from the brief.

| Component | Bounded data | Shared parameter behavior |
|---|---|---|
| SpatialCity | seed, count, columns, camera_radius, camera_height, orbit_degrees | Three instanced buildings, frame-driven orbit and traffic; stable geometry |
| QuantityMatrix | count, columns, registered asset_keys | One large image becomes a counted matrix of registered images |
| NodeNetwork | seed, count ≤64, columns, source_node, effect_parameter_id | Stable node IDs and edges survive layout changes; influence follows shortest graph hops |

`spatial-state.ts` holds deterministic geometry/count/topology functions. `spatial-kit.tsx`
renders them with Three/R3F, SVG and registered `Img` assets. Animations use explicit Remotion
frames and bounded semantic parameters, never a wall clock, `Math.random` or R3F `useFrame`.
The shared renderer loads the spatial module only when needed and blocks frame capture until
React has committed it; resolving an import alone previously produced empty captured frames.
ThreeCanvas has its own render readiness gate. The renderer selects Chromium `swangle` for
SpatialCity so software WebGL works in this headless environment without a discrete GPU.
Build/render environments need the locked Three/R3F/Remotion dependencies and WebGL support.

## Contracts and authoring

Each spatial entity requires `spatial` and a declared `parameter_id`. Values normalize through
the parameter's declared finite minimum/maximum. `effect_parameter_id` is only valid for a
network. Node count/source are checked before rendering; image matrices need nonempty unique
registered keys. Image URLs/paths are not accepted as keys. Matrix keys participate in native
plan declarations, asset usage/binding review, canonical receipts, source fingerprints and ZIP
exports just like other registered artwork. No provider inference occurs inside components.

An `immersive=true` entity occupies a 1920×1080 logical stage, alone in its shot, with
`show_heading=false`. It cannot bind to a device or cover a physical object scene. Ordinary
semantic entities retain the previous 1720×650 bounds. Smaller non-immersive spatial panels
preserve aspect ratio. Root continues to own CJK fonts, captions and audio. `neon_horizon`
adds a night palette; title, content, shape and artwork remain editable data/source.

Use narration-anchored `action=parameter` events, visible-result expectations and held result
frames. Measured narration compiles through the existing timing path. The fixed sample uses
explicitly estimated draft anchors with a start-edge anchor near the beginning of each shot.
It does not fabricate word alignment. Scene FPS remains 30; 60fps requires a separate
end-to-end timing, caption, sound and validation migration.

The native Agent receives these capabilities, the material catalog and requirements for
each scene:key binding. This makes the components available to planning and actual authored
source. It does not demonstrate that an unconfigured native provider can autonomously produce
an unseen scene. Unsupported subjects still need appropriate SVG/TSX or configured image
services under existing isolation; a procedural city is not a general 3D asset generator.

## Verification and fixed sample

Run `.venv/bin/python scripts/check.py`, configured `npm run test:ui`, then:

```bash
CHROME_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/verify_spatial_scenes.py
```

The verifier accepts no arguments. Its only authored dispatcher is the existing reviewed
`examples/reference-mechanisms/Video.tsx`, with fixed repository data in
`examples/spatial-storytelling/scenes.json` and protected platform modules. It cannot run
uploaded/model source. It renders the city, registers three of its actual stills through
project-image import (cropping away titles/captions), requests/consumes their receipts, then builds/previews/renders the full
28-second project. Stills are original rendered city illustrations, not camera photographs
or image-model output. No reference-video pixels or audio are reused.

Checks include geometry determinism, seed differences, camera bounds, matrix counts, stable
node/edge identities, shortest-hop reachability, asset provenance, unchanged source hashes,
continuous clip metadata, full MP4 decode and per-scene frame differences. Browser checks
move actual node SVG positions and persist numeric edits. Frame changes prove changes exist,
not that every arbitrary authored scene is semantically or artistically correct.

Outputs: `.verify-spatial-scenes/final/video.mp4`, `review.jpg`,
`Spatial_Storytelling_Project.zip`, `verification.json`; durable repository evidence is
`docs/verification-spatial-scenes.json` and `goals/2026-11-23-spatial-storytelling.md`.
The sample is a silent 1080p30 visual draft. Native/image/TTS inference, professional voice,
Docker/gVisor deployment and full human playback/listening are separate acceptance. Production
still requires the existing isolated renderer and exact-current-source review gates.
