# Content strategy architecture

Product semantics: [positioning-and-content-taxonomy.md](../product/positioning-and-content-taxonomy.md).
This implementation adds editorial structure to the existing author/build/observe/repair loop.
It does not replace the native Agent with keyword routing or restrict arbitrary TSX.

## Domain boundaries

`Brief.editorial` is the requested creative contract. Primary purpose (`intent`) has six
canonical values plus auto. `secondary_intents` allows up to two distinct canonical purposes,
excluding the primary. `subject_kind` is separate from purpose. `audience_description` and
`audience_level` refine the existing `Brief.audience` category. Up to four unique
`presentation_forms` express the requested visual treatments. Core message and viewer takeaway
remain separate text fields. Publishing profile, rendering mode, voice, resolution and design
pack retain their existing responsibilities.

The canonical catalog lives in `content_taxonomy.py`. Capabilities and the authenticated
`GET /api/v1/content-taxonomy` return the same labels, questions, suggested arcs, structural
requirements and success criteria. The UI consumes this catalog; it does not maintain a second
set of selectable purpose labels. `scripts/export_contracts.py` exports the catalog and schemas.

`StoryboardIR.editorial_request` keeps the current request in editable exports and renderer
props. `EditorialPlan.strategy` is the resolved strategy: canonical purpose/subject, audience,
forms, rationale, success criteria and an ordered `NarrativeBeat` outline tied to scene IDs.
Historic plans may have strategy=null. New native engineering creator plans must include it.
Standalone native/storyboard schemas can also carry EditorialPlan. Compatibility drafts leave
resolved strategy absent and display their incomplete editorial status explicitly.

## Resolution and validation

Explicit purpose/subject/depth/form choices constrain the plan. Auto is resolved semantically
inside the existing planning call using full context, with a recorded rationale; no classifier
regex or keyword dispatch is added. Profiles are prompt guidance, not fixed render templates.
The existing evidence IDs continue to ground assertions.

Before TTS, validation checks that explicit enum choices were honored, requested forms are
included, auxiliary purposes match, and the outline covers every actual scene in order exactly
once. Every strategy ends in a conclusion. Minimum functions vary by primary purpose:

| Purpose | Required functions |
|---|---|
| introduction | orientation |
| explanation | definition or mechanism |
| analysis | evidence or comparison |
| viewpoint | evidence, plus counterargument or limitations |
| advice | decision, plus steps or application |
| tutorial | steps and check |

New engineering output is validated inside the bounded native repair loop: typed response,
shot/storyboard consistency, material references, scene/evidence validation and creator
publication requirements must all pass before planning succeeds. The configured
`native_agent_repairs` bounds retries; exhaustion fails without a template fallback.
Repair feedback uses controlled platform messages, never raw validation inputs, invented
asset/evidence names or provider credentials. Engineering actions use the same typed-response
repair boundary. `ProductionPlan.editorial` is authoritative; the optional duplicate
`storyboard.editorial` must be null or identical, and saved revisions clear the nested copy.

A filled structural function does not prove a good argument or tutorial. Native review must
consider the actual script, images and purpose-specific success criteria. `purpose_fulfillment`
must reach 4/5 for a creator plan containing strategy; all prior publication, visual and motion
review requirements remain. Unmet criteria belong in review.issues. This review is still not
human playback/listening certification.

Actual runtime insertion registers the observed scene with the preceding argument beat. The
helper is idempotent for recovery and does not manufacture an execution or experimental claim.
The effective production plan is reserialized after actual timing/runtime changes.

## Revision and migration

All four dimensions live in Brief.editorial, so the existing whole-object comparison triggers
replanning when any changes. Studio can edit targets in a saved revision and posts the edited
request as Brief when forking. The original revision remains immutable. Narration reuse is still
based on exact text/provider/voice cache keys; changed source/props invalidates visual hashes.
Studio marks locally edited targets as pending, hides old strategy rationale/criteria and
shows the edited request until a new version is planned. Reverting the request restores the
saved strategy display. Title, language or production-mode changes also invalidate saved
storyboards; a new title invalidates understanding metadata. Accent-only changes synchronize
presentation metadata while keeping the script. These are separate from voice invalidation.

The deprecated legacy `intent=knowledge` is accepted as an exact data migration: intent becomes
auto, subject becomes knowledge only if no explicit subject was supplied. Existing core text
and explicitly selected subjects survive. This is not a prompt classifier. New schema and UI
advertise only the six canonical purposes. Older saved plans without strategy remain readable
and receive a review warning; they are not silently certified as newly classified content.

Renderer contracts carry request and strategy without changing typography, audio or TSX edit
permissions. Source/props/template fingerprinting, cancellation, lease fencing and credential-free
isolated execution remain intact.

## Verification

Six authored JSON examples in examples/content-strategies have distinct questions, messages,
arcs and acceptance criteria. `scripts/verify_content_taxonomy.py` validates these contracts and
prepares docs/verification-taxonomy.json. They are fixtures, not native model responses.
Backend tests cover wrong intent/subject/depth/forms, duplicate choices, legacy migration,
auto behavior, outline coverage, runtime recovery and score/hash gates. Browser coverage checks
six selectable purposes, independent dimension submission, truthful draft status and replanning.
The trusted creator rendering fixture also compiles and renders with the expanded contracts.
Real native quality across all six types remains target-deployment acceptance.
