# Creator publication contract

The default presentation is `creator`: videos express an audience-facing viewpoint,
advice, project analysis, knowledge or explanation. The UI supplies content intent,
optional core message/takeaway and optional account/series brand. `video_mode` still
selects engineering vs compatibility execution; it does not select editorial purpose.

## Contracts and pipeline

`Brief.editorial` contains intent, subject_kind, core_message and viewer_takeaway.
New native creator production plans require `EditorialPlan`: audience question,
central message, hook, evidence-linked support, conclusion and `CoverSpec`.
Scene.role is independent of Scene.type; the first and last roles are opening/closing.
Existing IRs remain loadable. Compatibility drafts arrange supplied facts and record
that deeper editorial planning is absent; they do not fabricate a model analysis.

All paths attach explicit presentation data. Publication validation runs after any
runtime insertion and before TTS, rejects unknown support IDs and obvious irrelevant
tool credits, and requires a cover plus opening/closing. Semantic relevance and
unsupported conclusions still need the native review; text matching is not semantic
certification. Reviewing the tool itself is allowed to name it. Verification/evidence
metadata are retained. Timed scene.disclosures support local code/example/sample
context, not permanent internal badges. Actual audio provenance remains in reports.

`presentation_profile=internal_demo|engineering_report` retains an explicit internal
use case. Do not use a profile change to represent a new runtime or TTS provider.
Changing the brief's editorial intent/message, audience or presentation requests a new
plan. Editing narration invalidates audio/cues through the existing revision/cache
rules. Visual-only cover edits keep narration and invalidate visual hashes.

## Rendering and review

The protected `src/presentation.tsx` provides topic-driven opening/closing cards,
selective disclosures and a registered `PublicationThumbnail` composition. Both
renderers export a separate `cover.png`. Engineering delivery selects the actual
thumbnail asset, never the first preview frame. Cover assets are included in the
editable export. Title text is readable at frame zero; narration has no inserted
silent logo bumper. Abstract marks are decorative, not model measurements.

The engineering preview includes the separate thumbnail, frame zero, 0.5s, 1.5s,
opening end, final frame and the existing per-scene samples. The maximum ordinary
frame budget is 128, sufficient for the 32-scene contract plus these samples. Existing
motion clips/contact sheets remain unchanged. All ordinary images, including the
thumbnail, must be named in the review. Creator output also requires content_focus,
cover_promise, opening_closing and viewer_presentation >= 4/5, with no open issues.
Source/props/template/assets remain covered by the existing project hash.

The platform can update protected templates; a runtime Agent cannot modify them.
The native and render container isolation, credentials, leases, cancellation and
professional voice/alignment policies are unchanged.

## Verification and scope

Run `.venv/bin/python scripts/check.py`, configured-Chrome `npm run test:ui`, and
`CHROME_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/verify_creator_publication.py`.
The last command runs only fixed repository-authored fixtures: two 6s 1080p silent
videos, first/closing-frame samples and an independent vector-scaled 4K thumbnail.
See `docs/verification-creator.json`; sampled image review is not full human playback
or listening. Native/provider quality, Docker/gVisor execution and real TTS are target
deployment checks. This change does not regenerate the old Ming video.

Only 16:9 1080p/4K remains supported. Vertical/square layouts, platform-specific
safe areas, advanced cover art direction and publishing integrations remain planned.

## Content taxonomy follow-up · 2026-11-18

The current primary purposes are introduction, explanation, analysis, viewpoint, advice
and tutorial. Subject/audience/form are independent. New native engineering creator plans
resolve EditorialPlan.strategy and require purpose_fulfillment >=4/5 in addition to the
existing publication scores. See content-strategy.md for exact contracts, legacy knowledge
migration, ordered scene coverage and scope. Older nullable strategies remain readable.
