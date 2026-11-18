# Semantic visual production

This implements the first reusable production path from the V5 proposal. It extends the
existing native author/build/observe/repair loop; it does not replace it or add a keyword
classifier. The twelve semantic components and an AssetImage compose software information,
state changes, documents and evidence. Physical devices remain useful for physical topics.

## Implemented data and rendering

`Scene.semantic_scene` contains a viewer question, bounded typed entities, narration-anchored
events and visible-result expectations. PromptInput, Conversation, TokenSequence,
ContextWindow, DocumentChunks, RetrievalResults, ModelBoundary, ToolCall, TaskState,
EvidenceStack, ApprovalGate and CodeWorkspace have distinct trusted render treatments.
Token examples and model boundary visuals are illustrations, not fabricated model internals.
Observed entities require evidence IDs; native planning validates supplied IDs.

`MotionShot.intent` records question, representation, rationale and visible result.
Semantic native plans require this structured intent. `asset_requirements` describe desired
original materials. Both planner paths receive the same toolkit guidance; actual semantic
selection remains the configured model's job. Compatibility drafts do not invent selection.

Entities may bind to a TV/monitor/laptop/phone `screen` with `bind_to`. The protected
ObjectScene callback calculates the display region in its local coordinate system. The
same SemanticPanel is used standalone and inside the screen. Device labels, state header
and confirmation button derive from one compiled state, so they cannot disagree through
independent static status strings. Geometry follows the device; there are no topic-specific
screen-overlay coordinates or postprocessing scripts in this path.

Legacy boards still load without semantic_scene. Physical and semantic layers can compose;
legacy diagram/motion remain exclusive with semantic scenes in this increment. General
arbitrary layer composition and advanced camera systems are future work.

## Measured state compiler

Events support transition, replace, append, select and highlight. Explicit from/to execution
states, valid item indices, prerequisite completion, conflicting overlapping updates, visible
content limits and a held result frame are checked. All causal events require expectations.
Narration phrases must exist. The existing measured word-span resolver is reused; draft
estimates are explicitly labeled. Compilation commits all three event representations only
after successful validation, clearing partial results on failure.

Changing narration/voice clears compiled semantic timing. Studio exposes editable entity
titles and anchor phrases, binding targets, expectations, measured/draft status and every
continuous preview for the selected scene. It never evaluates generated code in the editor.

## Real mediated material creation

EngineeringAction adds request_assets and inspect_asset. Native CLIs keep their restrictive
permissions; the controller performs these tools. `component_svg` creates an original
illustrative document/result SVG from a typed title and rows, embeds a subset of the required
CJK font, and creates a companion PNG from the same input. It is a specific controlled
material factory, not an arbitrary SVG interpreter or a universal image generator.

Receipts record request hash, font/factory version, actual SVG and companion PNG hashes,
geometry and provenance. Idempotent requests reuse the content; replacing an ID invalidates
build/preview/review and removes unreferenced generated files. Cancellation/lease guards run
before creation and before publication. The pipeline's existing fenced persistence stores
receipts inside the tenant-scoped engineering checkpoint. Replays are idempotent; no exactly-once
billing claim is made. The project budget is 24 registered assets and 8 MiB of active bytes.

Workspace recovery revalidates the typed request, regenerates controlled output and checks
hash/path consistency before restoring files. Neither recovered SVG text nor arbitrary paths
are trusted. A changed factory/font version fails explicitly instead of loading stale output.
Native calls receive actual companion PNGs as image context. inspect_asset checks current file
bytes and metadata; final SVG appearance is still reviewed through actual rendered frames.

Use AssetImage.asset_key with the request ID; props.generated_assets is platform-owned.
Build rejects missing keys. Export includes SVG/PNG assets, inputs/provenance receipts and
source. `image_service` is explicitly unavailable: it fails without substituting another
provider. ChatGPT's image-generation tool is not treated as an application integration.

## Shared preview, manifest and review

Both trusted paths use semantic-kit.tsx. The native Agent must still author a real Video.tsx
and compose SceneRenderer itself; the default component still throws before authoring.
Root remains responsible for audio, captions and disclosures. Thumbnail composition also
uses the trusted semantic renderer, including platform-generated asset mappings.

RenderPlan records source dependencies, actual public asset hashes, resolution, per-scene
fingerprints, semantic bindings and expectations. It is included in the fingerprinted props.
These keys are dependency evidence; rendered-scene caching is NOT implemented. Existing
custom source remains included in the full workspace fingerprint.

The trusted preview planner covers before/during/after frames for every semantic event and
continuous windows that include late results. Overlapping windows merge only within a bounded
five-second budget. Existing legacy continuous sampling remains. More than the bounded frame
budget fails explicitly rather than discarding late evidence. Render tools validate causal
clip coverage and dimensions; Studio shows every clip, not only the first one.

Semantic review must name every `scene_id:expectation_id` and score semantic_accuracy >=4,
while preserving all prior purpose, publication, object, motion and exact-source review gates.
An image difference is only a basic observation; it does not prove semantic correctness or
human understanding. Native review is not human full watching/listening certification.

## Verification and remaining work

`examples/semantic-scenes` contains fixed Agent, RAG and component-gallery data. The explicit
`scripts/verify_semantic_scenes.py` runs ONLY its fixed repository-owned dispatcher and data,
never external or model-authored TSX. It creates a real original asset, renders the engineering
wrapper and native-4K compatibility output, and checks actual result changes and late-event
coverage. Draft timing is intentional: this is not native inference, business execution or TTS.

Backend checks cover invalid references/cycles, state ordering, budgets, measured timing,
asset recovery/idempotency/cancellation/isolation, actual byte checks and protected modules.
A browser flow checks actual nested screen geometry, state display, version editing and
capability truth. The existing object and creator fixtures remain regression checks.

The V5 proposal remains the broader roadmap. Image/video/3D services, arbitrary layer graphs,
a general media normalization/FFmpeg backend, scene-video caching, OCR-based layout evaluation
and real unseen-topic model acceptance remain separate work. Existing runtime capture can
still be used through its established adapter; this increment does not claim new capture
providers. Current code-drawn semantic UI avoids the high-resolution video-overlay patching
used for the earlier authored Agent sample, but does not establish that all video decode
performance issues are fixed.

## V5 status mapping

| V5 requirement | Current implementation | Acceptance limit |
| --- | --- | --- |
| Visual intent and scene understanding | Typed shot intent, viewer question and model guidance | Unseen-topic model decisions still require a deployed native provider |
| AI information and state visuals | Twelve semantic treatments and typed causal events | Token/model diagrams are illustrations |
| Screen binding | Shared protected content in device-local display regions | TV, monitor, laptop and phone only |
| Asset factory | Original document SVG, companion PNG, bounded workspace receipts | No connected image/video/3D generation service |
| Causal review | State validation, exact expectation list, before/during/after and late continuous windows | Sample review is not full human viewing/listening |
| Unified rendering | Shared semantic renderer and RenderPlan dependency evidence | No arbitrary layer compositor, general FFmpeg backend or scene-video cache |

The complete [V5 target proposal](visual-production-v5-target-cn.md) is retained separately.
Generated SVGs embed the font license and a renamed font subset; exported projects include
public/FONT-LICENSE.txt. The companion PNG is a separately drawn review aid, not a claimed
pixel-identical SVG rasterization. Actual SVGs must still be reviewed in the rendered scene.

## Deployment and recovery review · 2026-11-18

The isolated render image copies both render.mjs and its local review-plan.mjs dependency.
A regression traverses local runtime imports against actual Dockerfile COPY inputs; a host
render alone cannot establish image packaging correctness. Rebuild the image after this
change. A real Docker build/run remains target-environment acceptance when Docker is absent.

Checkpoint recovery validates the entire asset batch and its count/byte budgets before any
publication. Both files and in-memory SVG/PNG cache fields are rebuilt canonically from typed
requests. A subsequent deduplicated request cannot republish unchecked checkpoint bytes.
Cached requests also verify current receipt checksums/paths. Repeated requests preserve
acceptance only if the complete workspace fingerprint is unchanged; repairs, replacements
or partial publication failures that change files invalidate build/preview/review evidence.

RenderPlan includes global presentation props (including theme and font) and trusted root
runtime modules as dependencies, excluding the manifest itself to avoid recursive refreshes.
This remains dependency evidence, not a rendered-video cache.

Tool receipts remain bounded at 128 KiB to accommodate the protocol's bounded frame and
multi-window lists. Each continuous clip must have integer scene-local bounds expressed in
global frames; its probed resolution, fps, frame count and duration must agree with that
range. Clip counts, frame counts, file-size limits and causal result coverage still apply.

## Illustrated production extension

The previous image_service-unavailable statement above describes the initial increment.
A configurable eva-image-1 gateway is now implemented alongside project-scoped PNG imports;
it remains unavailable until an actual gateway is deployed/configured. Assets now support
raster bytes/real previews, retained recovery, 24 assets/64 MiB active bytes, and preserved
legacy SVG request hashes. Full-frame registered backgrounds, unframed AssetImage artwork,
per-shot colors and measured transform events reuse existing compiler/review/render gates.
The automatic illustrative EvidenceStack footer was removed; provenance remains in reports.
See project-owned-visual-production.md for the current contract and verification boundaries.
