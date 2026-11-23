# Content-driven asset, scene and motion creation

## Product goal

The engineering Agent turns a new subject into appropriate original materials, composition
and causal motion. City/matrix/network components are optional vocabulary. A successful fixed
sample does not establish automatic creative quality on a new subject. The native Codex/Claude
engine remains the author; the platform supplies contracts, dependencies, material tools,
measured timing, isolated rendering, observation/repair and versioned evidence.

| Need | Engineering path | Evidence |
|---|---|---|
| Recognizable vector artwork | Author React/SVG modules under src/assets | Source hashes and actual rendered frames |
| Procedural 2D/2.5D scene | Author Canvas/React/SVG composition and deterministic state | Material/scene bindings and continuous previews |
| New 3D subject, environment or camera | Author Three/R3F/ThreeCanvas; declare technique three | General software-WebGL selection and isolated rendering |
| Illustration/photo/cutout | Configured image_service or project_image | Canonical receipts, ownership and binding review |
| Operation/UI explanation | Supplied real captures and authored emphasis | Capture evidence; no invented successful operations |
| Relationship diagram | Optional existing semantic/object/spatial kits | Same timing and visible-result gates |

There is no topic-to-template router or new fixed-subject catalog. Unsupported objects should
get appropriate new source/artwork rather than a stock box carrying the noun. The existing
image service is not silently substituted by code or another provider.

## Contracts and timing

`Scene.creation` contains visual_goal, free composition, six-digit palette, techniques,
scene_source, elements and events. Elements describe actual appearance and role:
subject/environment/prop/annotation/camera. Source elements bind source_file; raster elements
bind a registered asset_key; capture/kit elements state their representation. At least one
subject is required. Source paths are canonical editable src TS/TSX paths.

Every **new engineering plan** provides creation for every shot. Historic plans remain
loadable without it. Native validation rejects missing new designs inside the bounded repair
loop. Grid/fan/count restrictions apply only to selected legacy motion specs, not custom scene
composition. The authoring payload also supplies current_scene_creation from actual props,
so saved edits remain authoritative when the historical plan describes an earlier revision.

Custom events use arbitrary target/channel IDs, spoken anchors, duration and concrete
before/change/after descriptions. They need no diagram pattern or fixed software action.
Targets/dependencies must exist; cycles and same-target/channel overlap fail. Different
channels can change together. The existing word-span resolver compiles actual timing into
compiled_creative_events, reserves a held result frame, and contributes event ends to measured
frame allocation. Draft timing remains explicitly estimated. FPS remains 30.

Authored source consumes the protected helper:

```tsx
const frame = useCurrentFrame();
const open = creativeProgress(scene, 'open-cover', frame);
return <Book open={open} palette={scene.creation!.palette} />;
```

Book is an authored component, not a built-in subject. The source may construct appropriate
geometry/camera paths using controlled dependencies. Animate from explicit frames, not a
wall clock or R3F useFrame. Root owns fonts/captions/voice. Custom creation opening/closing
shots are not covered by default bookend cards. SceneRenderer is conditional on kit use.

## Materials, reuse and acceptance

Build checks each declared source exists as tracked authored bytes, is not a symlink, and is
inside the editable contract. Registered image keys enter existing declarations, receipt and
visibility review even without semantic_scene. Full workspace hashes still cover every source
file/dependency, including imports not explicitly named as source artwork.

Build evidence and ZIP export include creative-manifest.json: current project hash, source
asset hashes, shot designs and compiled motion. Source/props/asset changes invalidate old
acceptance. Parent revision checkpoints retain actual modules for reuse. This is project-owned
reusable source; promotion into a global executable catalog remains a separate reviewed
operation, not automatic publication of arbitrary generated code.

Every custom event enters before/during/after frames and continuous causal coverage. Review
must name scene:element:id and scene:event:id and score subject_fidelity, scene_composition and
creative_motion ≥4, alongside all existing publication/material/timing/hash gates. Generic
visual scores alone cannot accept these scenes. These are structural checks plus native
observation, not independent pixel-level proof that arbitrary source depicts every claim.

Studio shows the goal, composition, objects and change sequence. It never evaluates authored
source; actual engineering previews still come from the isolated renderer. No host fallback.

## Real new-topic verification

Routine tests cover native repair/history compatibility, bindings, measured motion, dependency
and range rules, recovery/export hashes, review rejection, generic Three selection and late
event coverage. The pure helper verifier only executes fixed protected platform modules.
Docker packaging tests include the new renderer capability module.

```bash
.venv/bin/python scripts/verify_engineering_deployment.py \
  --provider codex --creative --expect-technique svg \
  --topic '通过在图书馆找书解释RAG，自主设计书本、书架和取书过程' \
  --output .verify-creative-deployment/report.json
```

Use --expect-technique three for a new 3D subject. The topic is input, not a coded case.
The verifier requires actual source artwork, matching hashes, creative review and causal
events after the real native/isolated job succeeds. --draft explicitly selects a silent timing
draft; professional acceptance requires configured Qwen and actual alignment. It consumes
provider quota and requires native credentials and Docker/gVisor. Preflight writes **blocked**
when unavailable, never a fixed-fixture success. Human viewing/listening remains separate.

Actual results: goals/2026-11-23-creative-production.md and
docs/verification-creative-production.json. The earlier 28-second fixed sample is not this
new-topic native creative acceptance result.
