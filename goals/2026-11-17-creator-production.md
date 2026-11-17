# Creator production contract

Scope: implement audience-focused editorial planning, distinct thumbnail/opening/closing,
selective viewer disclosures, creator defaults in both render paths, publication review
and revision invalidation. Retain native-provider, isolation, audio/evidence and cancellation rules.
No new video or Ming inference is requested in this code change.

Acceptance: `.venv/bin/python scripts/check.py`; configured-Chrome `npm run test:ui`;
fixed, repository-authored creator fixture rendering with first-frame/thumbnail samples.
No deleted tests, skip markers or weakened assertions. Record unavailable services honestly.

Baseline: clean main at d1d8bf2deb10b2cc2cee65b0d156fd477a8a4784.
Initial check: blocked because the existing virtualenv lacks ruff. Installing declared dev dependencies.

Implementation and delivery evidence will be appended here.

## Delivery

- Implemented shared editorial contracts/policy, native planning constraints, creator defaults,
  separate thumbnail composition, readable opening and topic-driven closing, selective viewer
  disclosures and independent cover in editable export. Protected presentation code remains
  outside runtime Agent edit permissions. Evidence, voice, isolation and lease rules preserved.
- Added creator controls and cover editing/download to Studio. Content intent/profile/audience
  changes request a new plan. Existing audio cache invalidation and current-source visual gates
  remain active. Native publication review adds four content/presentation scores and the cover.
- `.venv/bin/python scripts/check.py`: ruff + 115 backend tests + TypeScript + Vite build passed.
- Configured-Chrome `npm run test:ui`: 7 browser flows passed (including creator data, first-frame
  visibility, no internal badges, cover changes and version persistence).
- `npm run format:check`, `git diff --check`: passed.
- Fixed `scripts/verify_creator_publication.py`: both actual 6s/180-frame/1080p outputs decoded;
  separate 4K thumbnail checked; ordinary previews include frame zero/opening end/final frame.
  Sampled first/closing/thumbnail images visually inspected for text and default branding.
- Rendering browser: Remotion Chrome Headless Shell from the current workspace. The first UI
  run detected a duplicate hidden title beneath the opening overlay; the renderer was fixed,
  the original test retained, and all 7 flows subsequently passed.
- Baseline check initially lacked declared dev dependencies; installing apps/api[dev] resolved
  it. Existing dependency deprecation and Vite chunk-size warnings do not block these checks.
- Limits: native Agent inference, Docker/gVisor execution, real TTS/listening and vertical layouts
  remain separate deployment/future work. Existing Ming deliverables were not regenerated.
