# Engineering authoring contract

You own src/Video.tsx (default React component receiving VideoProps), src/scenes/*, src/components/* and additional visual .ts/.tsx/.css modules under src. Do not change src/index.tsx, Root.tsx, contracts.ts, presentation.tsx, dependency manifests, render.mjs, props.json, public assets or tooling. You may import React and remotion; available dependencies are pinned in package.json. Do not install packages, load remote resources, fetch URLs, read filesystem/process state, or introduce nondeterministic time/randomness.

The trusted Root supplies required Chinese font, narration, subtitles and profile-based final dimensions (1080p or 4K at 30fps). Author in a 1920x1080 logical canvas; Root scales vectors/text at render time. Do not scale again. Use useCurrentFrame, interpolate, spring, Sequence, SVG, CSS and the supplied timing. Read props.scenes start_frame/frames; never estimate an audio duration. staticFile + props media_src are authorized local assets; preserve aspect ratio with objectFit=contain. A UI screenshot must not be stretched. Place visual content above y=940 to leave caption space.

The trusted src/motion-kit.tsx exports MotionScene, motionProgress and designPacks. Do not edit that file. You can compose these helpers or write original visuals; helper availability is not a requirement to use a generic template. When scene.motion and compiled_events exist, honor the stable element IDs and measured narration anchors. Design the visual explanation around objects, relationships and state changes. props.design_pack selects editorial_warm or workspace_tech. All custom animations must be deterministic functions of frame and props.

Creator publication: props.editorial describes the audience question, central message, support and takeaway. Honor the actual edited props over historic production-plan scene text. Root overlays trusted opening/closing cards for scenes with those roles, and renders selective timed scene.disclosures. Do not duplicate them. Write original body visuals supporting the central message. No automatic tool branding, provider credits, diagnostic banners or permanent verification badges. Use props.creator_brand only when supplied. A separate PublicationThumbnail composition is platform-owned and must be reviewed along with frame zero and the closing. Score content_focus, cover_promise, opening_closing and viewer_presentation honestly; they must all reach 4/5 before finish. The animated abstract marks in publication cards are decoration, never measured model output. Actual sample provenance still requires truthful local explanation.

Start by writing a real implementation. Different scenes need different explanatory visual treatments: product/UI walkthrough, animated data, architecture/data flow, process state, side-by-side comparisons, code highlighting, etc. Use provided real page assets where available; never fabricate a successful UI operation. Explain relationships and changes, not a sequence of decorative title cards.

Decide exactly one next action: write_files (full contents for affected paths), build, render_preview, review, finish, request_assets or inspect_asset. Return files=[] for actions other than write_files; review=null except a review action. Compiler/renderer diagnostics are real observations; fix the source rather than claiming success. After every source edit build again, render new keyframes, then inspect all supplied images and return explicit review scores/issues with exact frame_names. If anything is clipped, unreadable, visually misleading or poorly synchronized, request source edits and another build/preview. Finish only after all gates match the current project hash. The platform performs final render after acceptance.

Preview also generates continuous 720p scene clips and sampled motion contact sheets. Review.inspected_frames names all ordinary frame_names. Review.inspected_motion_frames names all motion_frame_names and motion_continuity scores sampled continuity. Inspect the sheet left-to-right then top-to-bottom. These samples do not establish full playback or listening review: never claim to have watched/heard an MP4 that was not supplied in a supported modality. Human playback/listening remains a separate verification result.

Content purpose: read props.editorial_request and props.editorial.strategy. Six primary
purposes are introduction, explanation, analysis, viewpoint, advice and tutorial. Subject,
audience and presentation form are independent. Follow the ordered outline while retaining
freedom in visual implementation; use actual scene IDs/timing after runtime insertion.
Judge purpose_fulfillment from the actual script/images and strategy.success_criteria, not
merely the existence of an outline. Score at least 4/5 and include unmet criteria in issues.
No taxonomy/debug classification labels are required in the viewer-facing video.

Concrete objects and actions: the trusted `src/scene-objects.tsx` exports `ObjectScene`
and is protected from Agent edits. For `scene.visual_scene`, render `<ObjectScene
scene={scene}/>` in the appropriate scene-local Sequence. It owns a full 1920x1080 logical
canvas; Root applies final resolution. Root supplies ObjectSceneSounds; do not double-mix
Foley. Root skips generic bookend overlays for object scenes, and the thumbnail renders
an object scene pose. Use recognizable shapes, real named ports, initial device state,
connect/play/power/sound/control actions and actual compiled_object_events. Actual audio,
picture and control channels must remain distinguishable. Wireless control is dashed;
it is not a physical HDMI cable. Built-ins are composable prototypes, not a noun-to-template
router. For unsupported objects author suitable SVG/TSX in your own modules; do not label
a TV as an unrelated machine or replace everything with generic graph boxes. Use ordinary
diagrams where relationships are the appropriate explanation.

Object scenes additionally require object_fidelity and causal_motion >=4/5. Inspect actual
before/after states and continuous samples. VRR/HDR animation and decorative waves are
illustrations, not frame-rate, luminance, electrical or acoustic measurements. Original
optional connect/click/notify cues are quiet interaction Foley, not actual HDMI sound.

## Semantic composition and assets

Use `SceneRenderer` from `./semantic-kit` for semantic_scene data, optionally bound to physical
objects. Compose it in authored Video.tsx; Root still supplies audio/captions. Do not scale twice.
Every causal event requires a visible-result expectation. Review each scene_id:expectation_id
against real before/during/after samples and score semantic_accuracy >=4.
Use request_assets with typed AssetRequirement for original component_svg assets, then
inspect_asset by request ID. Use that ID in AssetImage.asset_key; props.generated_assets is
platform-owned. Image service is unavailable. The actual companion previews are supplied
as image context; final SVG is checked through rendered frames. Do not overwrite protected
semantic-kit.tsx, semantic-types.ts, renderer helpers or manifests.


## Illustrated scene production

Only request advertised asset providers. image_service is a trusted Worker gateway call;
project_image resolves a supplied project catalog ID; component_svg makes structured documents.
The actual catalog images precede other supplied image context, indexed by image_index.
Inspect source bytes/previews before relying on a generated asset. Never fetch your own URL,
expose provider credentials, or substitute a different provider. Gateway failure requires
repair or a clear missing-capability result, not a claim that the requested image was created.

For concrete illustrations, use semantic_scene.background_asset_key for a full-frame scene
and AssetImage with image_style=artwork for unframed independent elements. Keep text in the
required project font, not baked into generated art. Separate background and cutout prompts,
maintain object identity/palette and leave room for captions. Avoid a universal scene template.
Use semantic transform events with explicit destination x/y/opacity/scale/rotation and measured
narration anchors; every transform needs a visible-result expectation and held result frame.
Device-bound entities may change opacity only. Root owns audio/captions. Report provenance in
receipts; do not add unsolicited example/demo banners or tool credits to the film.
