# Engineering Video Agent — repository instructions

## Product contract
Build an Agent that authors, builds, renders, observes, repairs and delivers a real Remotion project. A JSON storyboard alone is not the final product. Preserve the existing template API as explicitly labelled compatibility mode.

## Working rules
- Read README.md, Roadmap.md and docs/design/engineering-agent.md before changing the execution model.
- Keep provider authentication outside generated-code build/render containers. Never execute uploaded or generated code on the application host as a fallback.
- Source, design, generated files, build logs, frames, reviews and final artifacts are versioned evidence.
- A file change invalidates prior build, preview and review gates. Acceptance must match the exact current source/props/assets hash.
- Generated code must be checked by a real compiler and renderer. Never call a fixture or fabricated response a real model integration.
- Professional output requires Qwen narration and real alignment. Never silently substitute eSpeak, silence, a template, or an unreviewed video.
- Fonts must load successfully. Tests passing, a valid codec, or an Agent saying “looks good” are not human quality certification.
- Keep cancellation, lease fencing, tenant authorization and bounded subprocess output intact.
- Do not delete tests, add skip markers, weaken assertions, or hide unavailable infrastructure.

## Code and documentation
Python domain/validation in apps/api/src/explainer; Agent orchestration in services/engineering; isolated tools in infra; reusable standalone Remotion project in packages/engineering-template. No provider secrets in generated projects or logs. Use typed contracts, stable artifact names and small modules.

Run .venv/bin/python scripts/check.py and npm run test:ui with a configured Chrome. Record real results in goals/2026-10-30-engineering-agent.md. Update Roadmap.md and design documents with implementation and verification limits. Markdown uses UTF-8; canonical README.md and AGENTS.md avoid case-only duplicate filenames on Windows.
