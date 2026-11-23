# Generated video project instructions

This is an editable Remotion engineering project. Read README.md, production-plan.json, props.json and visual-review.json before modifying it.

- Put visual implementation in src/Video.tsx and src/scenes or src/components; preserve trusted Root/index/contracts unless deliberately changing the standalone project's runtime contract.
- Audio and captions use exact compiled scene frames; do not change narration timing casually.
- Preserve image aspect ratios and the bundled CJK font. No remote fonts/assets or nondeterministic Date/random animation.
- Run npm run check, npm run preview and inspect frames before npm run render.
- When editing untrusted generated code, use an isolated, no-network environment without credentials.
- Compiler success and an Agent score do not replace visual and listening review. Regenerate reviews after source or props changes.
- Preserve platform spatial-kit.tsx/spatial-state.ts. Use bounded semantic spatial data and
  declared parameters; QuantityMatrix keys must resolve registered bundled assets. Immersive
  spatial shots require one entity, no physical stage and show_heading=false. Camera and
  network changes must use compiled frame-driven events; never introduce wall-clock motion.
- Creation scenes author their specified material/scene modules and implement compiled_creative_events
  with protected creative-kit.ts. Kits are optional. Preserve identities, registered keys, source
  hashes and visible causal results. Technique three enables software WebGL for any Three subject.
