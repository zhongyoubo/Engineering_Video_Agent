# Engineering Video Agent — repository instructions

## Product contract
Build an Agent that authors, builds, renders, observes, repairs and delivers a real Remotion project. A JSON storyboard alone is not the final product. Preserve the existing template API as explicitly labelled compatibility mode.

Read docs/product/positioning-and-content-taxonomy.md and docs/design/content-strategy.md for content changes. Six primary purposes are introduction, explanation, analysis, viewpoint, advice and tutorial. Keep subject, audience and visual form independent. Auto is semantic model resolution, never keyword routing; compatibility drafts must not fabricate resolution or quality acceptance.

## Working rules
- Read README.md, Roadmap.md and docs/design/engineering-agent.md before changing the execution model.
- Keep provider authentication outside generated-code build/render containers. Never execute uploaded or generated code on the application host as a fallback.
- Source, design, generated files, build logs, frames, reviews and final artifacts are versioned evidence.
- A file change invalidates prior build, preview and review gates. Acceptance must match the exact current source/props/assets hash.
- Generated code must be checked by a real compiler and renderer. Never call a fixture or fabricated response a real model integration.
- Professional output defaults to Qwen and requires the explicitly selected Qwen/Edge/Ming adapter plus real alignment. Provider availability is not listening certification. Never silently substitute eSpeak, silence, another provider, a template, or an unreviewed video.
- Fonts must load successfully. Tests passing, a valid codec, or an Agent saying “looks good” are not human quality certification.
- Keep cancellation, lease fencing, tenant authorization and bounded subprocess output intact.
- Do not delete tests, add skip markers, weaken assertions, or hide unavailable infrastructure.

## Code and documentation
Python domain/validation in apps/api/src/explainer; Agent orchestration in services/engineering; isolated tools in infra; reusable standalone Remotion project in packages/engineering-template. No provider secrets in generated projects or logs. Use typed contracts, stable artifact names and small modules.

Run .venv/bin/python scripts/check.py and npm run test:ui with a configured Chrome. Record real results in goals/2026-10-30-engineering-agent.md. Update Roadmap.md and design documents with implementation and verification limits. Markdown uses UTF-8; canonical README.md and AGENTS.md avoid case-only duplicate filenames on Windows.

V4 work also records evidence in goals/2026-11-16-visual-explainer-v4.md. Use docs/design/visual-explainer-v4.md for the implemented visual/motion, output-profile, preview and MCP contracts. Preview motion contact sheets are sampled evidence; they do not prove full playback/listening. Preserve frame/clip hash invalidation and the protected motion-kit.tsx. The fixed repository fixture may be rendered by its explicit verification script; this never enables host execution for user or model-generated code.

Concrete visual work: read docs/design/object-scenes.md. Prefer recognizable objects, named
ports, causal actions and visible results for concrete subjects. Select semantically; never
turn every noun into a graph box or keyword-routed device template. scene-objects.tsx is
platform-owned and protected like motion-kit.tsx. Unsupported subjects may use authored
SVG/TSX under the existing isolation; do not fake an image-generation service or hardware
measurements. Fixed platform fixtures alone may run through verify_object_scenes.py.

Semantic production: read docs/design/semantic-production.md. semantic-kit.tsx and
semantic-types.ts are protected platform code. Software concepts use semantic entities
and explicit causal results, selected semantically rather than by keywords. Fixed
verify_semantic_scenes.py alone may host-render its fixed reviewed platform dispatcher;
never substitute arbitrary uploaded/model TSX. Preserve native source authoring, isolation,
voice truth, tenant checkpoints, asset provenance and complete source-hash review gates.

Project-owned illustrated production: read docs/design/project-owned-visual-production.md.
Image services run only through mediated Worker tools; project-image IDs require both tenant
and project membership. Retain bounded canonical PNG receipts and preserve legacy SVG keys.
The explicitly reviewed verify_production_assets.py may host-render only its fixed repository
source/storyboard and hash-pinned media; it is not native/image inference or an arbitrary
source runner. Real unseen-topic acceptance uses verify_image_production_deployment.py on
configured isolated infrastructure. Record this work in goals/2026-11-18-production-assets.md.

Reference corrections: read docs/design/reference-production-corrections.md. Preserve global
asset identities, complete code visibility, measured event budgets, native material-binding
review and numeric flow conservation. theme.tsx, code-view.tsx and mechanism-kit.tsx are
protected. verify_reference_mechanisms.py and verify_visual_contracts.cjs execute ONLY fixed
reviewed repository data/modules; never accept user/model source/path arguments or enable a
host fallback. Record execution in goals/2026-11-18-reference-optimization.md.

Spatial storytelling: read docs/design/spatial-storytelling.md. spatial-kit.tsx and
spatial-state.ts are protected platform modules. Preserve frame-driven 3D readiness, stable
node/edge identity, bounded shared parameters and registered matrix-asset binding review.
verify_spatial_scenes.py may host-render only the existing fixed reviewed repository
dispatcher and fixed bounded scene data; it accepts no source/path arguments. This exception
never permits user/model code or native-provider host execution. Record results in
goals/2026-11-23-spatial-storytelling.md as well as the main execution goal. Keep 30fps,
estimated draft timing and absent native/TTS/deployment certification explicit.

Content-driven creation: read docs/design/content-driven-creation.md. New engineering plans
require Scene.creation; historical plans may omit it. SVG/Canvas/Three source artwork is
authored in the ordinary isolated project, never executed by the application or Studio.
Protect creative-kit.ts/creative-types.ts. Preserve custom causal timing/held results, coverage,
source/image binding, creative manifests and dedicated review. Existing components are optional
vocabulary, never the creative ceiling or a topic keyword router. Fixed helper tests do not
establish real native creativity. Record goals/2026-11-23-creative-production.md and the main goal.

Curated material packs: read docs/design/material-packs.md. Pack selection resolves only
reviewed hash-pinned offline manifests, protects src/vendor and library-model.tsx, retains
licenses and invalidates all source/preview/review gates on changes. Binary PNG/GLB requests
use canonical receipts; GLB is embedded, not a remote loader or 3D generation service.
verify_material_packs.py may host-render ONLY its fixed reviewed examples/material-packs/Video.tsx
and curated repository media. It accepts no arguments; never use it for uploaded/model source.
Record results in goals/2026-11-23-material-packs.md and the main execution goal.
