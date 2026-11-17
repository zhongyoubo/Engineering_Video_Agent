# Content taxonomy and positioning

Baseline: clean merged main a7ca80d961114db4b6270bdf5fa121ebb6f80ec8.
Scope: six primary purposes; independent subject/audience/forms; structured resolved
strategy, purpose-specific narrative/review guidance, legacy knowledge migration,
Studio creation/revision persistence and design/API/user documentation.
Preserve arbitrary TSX, evidence, voice alignment, source-hash gates, isolation and leases.
No deleted/skipped tests or weakened assertions. No TTS/inference or new video requested.
Acceptance: scripts/check.py, configured-Chrome npm run test:ui, contract/fixture
validation and precise recorded implementation/deployment limits.

## Implementation and verification

- Six canonical purposes; independent subjects, audience description/depth and visual forms.
  Up to two auxiliary purposes and four forms. The same catalog feeds API/capabilities/UI.
- Exact old knowledge migration preserves explicit subjects and core text. Auto resolution
  stays inside the native semantic planning call; compatibility drafts keep it unresolved.
- New native creator plans require a resolved strategy with rationale, purpose criteria and
  ordered actual-scene coverage. Before TTS, explicit enum/form constraints and purpose
  structure are checked. Native review requires purpose_fulfillment >=4/5 on current hashes.
- Studio can create and revise all dimensions. Changing any dimension replans; existing
  audio cache/voice and immutable revision rules are preserved. Runtime scene insertion
  updates the outline idempotently, and the effective production plan follows actual props.
- Added product/design/API/user/data-model docs and six authored example fixtures.
- Baseline scripts/check.py: 115 tests, ruff, TypeScript/build passed.
- Updated scripts/check.py: 143 tests, ruff, TypeScript/build passed.
- Configured-Chrome npm run test:ui: 8 flows passed, including four-dimension submission,
  truthful incomplete draft status, target editing and replanning.
- scripts/verify_content_taxonomy.py: all six authored strategy contracts passed.
- scripts/verify_creator_publication.py: both fixed 6s/1080p videos decode; independent
  4K thumbnail and opening/final samples checked. See verification-creator.json.
- No test removed/skipped or assertion weakened. Existing dependency deprecation/chunk
  warnings remain non-blocking. Real native/TTS/isolated deployment quality across six
  purposes has not been certified by these fixtures. No new Ming video was requested here.

### Final command results

```text
.venv/bin/python scripts/check.py
All checks passed! (ruff)
143 passed, 5 warnings
npm run typecheck: passed
vite build: built successfully (existing chunk-size advisory)

CHROME_EXECUTABLE=<configured Headless Shell> npm run test:ui
8 passed (40.8s)

.venv/bin/python scripts/verify_content_taxonomy.py
Six authored editorial strategy contracts passed

CHROME_EXECUTABLE=<configured Headless Shell> .venv/bin/python scripts/verify_creator_publication.py
engineering + compatibility: 1920x1080, 180 frames, 6.0s, decode passed
independent thumbnail: 3840x2160

npm run format:check
All matched files use Prettier code style!

git diff --check
(no errors)
```
