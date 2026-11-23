# Editable Remotion project

Content-driven creation uses Scene.creation and compiled_creative_events. Native-authored
SVG/Canvas/Three materials live in src/assets and scenes in src/scenes; existing kits are
optional. Use protected creativeProgress for measured causal changes. creative-manifest.json
records actual source material hashes and bindings. Technique three enables software WebGL
for any authored subject. Model-authored code still runs only under isolation.

Generated source lives in src/Video.tsx and optional src/scenes or src/components. Trusted Root.tsx supplies required CJK font, audio, captions and composition dimensions. props.json supplies actual compiled scene frames and authorized public media.

Install Node 20.19+, FFmpeg and a compatible Chrome. Run npm ci, npm run check, npm run preview, npm run render. Set CHROME_EXECUTABLE if needed. Use an isolated environment for model-generated source; never render untrusted projects on a workstation with credentials. The application runs this project in an isolated, no-network tool container.

Dependencies and lockfile are platform-controlled. Source, production plan, journal and visual review are included. Output is 1920x1080, 30fps. Review quality separately from successful compilation/decoding.

SpatialCity, QuantityMatrix and NodeNetwork compose through SceneRenderer with bounded
semantic_scene parameters and narration-anchored events. QuantityMatrix uses registered
bundled asset keys; repeated image tiles do not imply distinct source images. A single
immersive spatial entity uses show_heading=false and cannot cover a physical object stage.
neon_horizon is the third shared design pack. City rendering uses software WebGL (swangle),
Three 0.181.1, R3F 9.4.0 and matching Remotion 4.0.538. Preserve frame readiness and stable
geometry/identities. This vocabulary is not a general automatic 3D asset service.

## Versioned material packs

Read the advertised material_library metadata and actual material_preview_index sheet. Use
search_materials with material_query (query/style/asset_type), then select_materials with the
COMPLETE desired material_refs list; [] clears selection. Component modules/symbols are
advertised by the catalog, staged at src/vendor/<pack>/<entry>, and cannot be edited. Declare
component references in shot.assets and creation kit elements.library_ref. Do not call borrowed
component paths authored source assets. Register PNG/GLB with provider=library_asset and exact
library_ref; bind asset_key to creation elements. props.generated_assets[key] is a local filename,
not a receipt object. Img/staticFile handles PNG; LibraryModel from ./library-model accepts
asset={props.generated_assets[key]}, finite width/height and frame-derived angle in radians.
Declare technique three for GLB. PNG is 2D; honor original pixel sizes. No npm install or remote
asset downloads. Preserve measured causal timing and inspect actual scene bindings; selecting
an entry does not prove visible consumption. Complete licenses stay in reports/source export,
not unsolicited in-film producer badges. See docs/design/material-packs.md in the source repo.
