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
