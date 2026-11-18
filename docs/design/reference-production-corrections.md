# Reference-production corrections

## Scope

The reference review found three reproducible defects (asset ID collisions, silent code
truncation and insufficient tail-motion budgets), incomplete theme propagation and a gap
between generation receipts and declared material use. This change fixes those paths and
adds reusable numeric mechanisms. It preserves native source authoring, measured voice truth,
credential-free offline rendering, tenant/fence checks and current-source review gates.

## Global material identity

Asset IDs are project-wide, including requirements declared inside different MotionShots.
ProductionPlan rejects two different requirements with the same ID; identical requirements
can share an ID intentionally. The controller rechecks planned identities before a paid
request and rejects conflicting payloads. Native planning requires every semantic background
and AssetImage key to have a declared requirement. Use scene-prefixed IDs for distinct art.
A deliberate revision can still replace one globally shared material and invalidate affected
source review; no silent scene-local override is inferred from a duplicate ID.

The asset-usage contract ties registered keys to semantic scene backgrounds/elements. A
permanently transparent declared element is rejected. Native review must name every
`scene_id:asset_key` binding in `asset_expectations` and score `asset_visibility >=4` from
actual frames. Deployment verification requires distinct generated image hashes, a generated
background, a used transparent cutout, measured motion on that cutout and accepted binding
review. Merely producing unused images cannot satisfy this structural acceptance anymore.

These are structural checks plus native visual inspection, not an independent pixel-level
proof that arbitrary authored TSX displays every declared object. Native custom code can
implement alternative renderings and must still be reviewed against actual preview evidence.
General occlusion/OCR detection and human viewing/listening certification remain separate.

## Full source viewport and issue bindings

`code-view.tsx` wraps the complete code string, preserves original source line IDs and pages
14 rendered rows at a time. Tabs expand to spaces; wide characters consume two width units.
No line or character is silently sliced away. Unfocused scanning progresses through pages;
`motion.code_focus` binds an element ID to `line` and optional `end_line`. A matching compiled
motion event selects that source region; larger regions progress through their own pages.
Out-of-range bindings fail schema validation. The row scan, source highlighting and related
issue card share the declared target/event instead of unrelated decorative timing.

This bounded viewport is not a syntax-aware editor or a general codebase explorer. Native
plans should select relevant real source excerpts and leave reading time; source provenance
and legibility review still apply.

## Tail events and timing constraints

The pipeline now calculates motion budgets from actual word boundaries before final frame
allocation. Legacy, object and semantic event endings reserve at least one held result frame.
Unconstrained target mode can extend a shot to fit its speech and events without trimming
voice or altering measured words. Locked frames, per-scene maximums and exact/max total limits
remain strict. An impossible constraint is explicitly rejected, not silently relaxed.

This repairs the concrete 3-second voice / 700ms ending-event failure. It does not claim an
unrestricted pre-authoring scene-replanning Agent: contradictory dependencies, invalid states
or impossible strict deadlines still require a valid revised plan. Estimated draft anchors
remain estimated and do not receive fabricated measured evidence.

## Shared theme

Protected `theme.tsx` owns both design packs. Motion code, semantic panels, object-stage
backgrounds, trusted captions, editor fallback colors and independent thumbnails reuse these
tokens. Semantic background/title overrides are optional; omitted values inherit the selected
theme. Intrinsic device colors, code foregrounds and imported/generated artwork keep their
own material colors; switching UI theme does not recolor baked image pixels.

Theme, code viewport and mechanism modules are protected from native file edits. Template
and source/public dependencies remain part of the existing workspace hash and render plan.
Material catalog entries point at the source module that owns their implementation.

## Parameter mechanisms

`semantic_scene.parameters` declares up to eight finite bounded numeric parameters:

```json
{"id":"strength","minimum":0,"maximum":1,"initial":0,"unit":""}
```

A semantic event with `action=parameter`, `target=strength`, `value=1` uses the existing
narration anchor and duration fields. It requires a visible-result expectation, checks range,
conflicts and dependency completion, and compiles to the same measured/draft event protocol.
The shared renderer interpolates this one value for all bound entities.

| Component | Binding | Behavior |
|---|---|---|
| Dial | parameter_id | needle follows the normalized numeric value |
| BranchTree | parameter_id | bounded branch depth follows the same normalized value |
| MetricBar | parameter_id | bar and displayed value follow that shared state |
| FlowReservoir | parameter_id + inflow_id + outflow_id + capacity | integrated stock controls fill level and labels |
| QueueFlow | same stock/rate bindings | queue stock, processed count and overflow follow the same recurrence |

Mechanisms are separate entities, not fixed topic templates. Bind a dial/tree/bar to one
parameter when the explanation needs causal linkage. For flow components `parameter_id`
holds **initial stock**; change rate parameters, not stock directly. Rates must remain
nonnegative. At the supported 30fps, each step adds arrivals, removes at most available stock
and records overflow above capacity. Stock + processed + overflow = initial stock + arrived.
Entities sharing stock/rates therefore show the same state. Frame history is cached only in
memory for that immutable scene during rendering; this is not a rendered-video cache.

These are illustrative educational state models unless the author supplies actual observed
values with evidence. They do not measure model internals or hardware. Counts/branch expansion
are explanatory geometry, not a fabricated reasoning trace or benchmark.

Studio exposes initial numeric parameters and preserves them through normal revision saves.
Agent planning receives schemas and toolkit guidance; it chooses representations semantically,
not via a keyword classifier. Arbitrary custom SVG/TSX remains available under isolation.

## Verification and release

`npm run test:visual` checks the real repository-owned pure rendering functions: complete
code preservation/pages/focus, shared parameter interpolation, branches, all five mechanism
components, stock conservation/capacity and semantic theme markup. It executes no user/model
source and is included in scripts/check.py.

`verify_reference_mechanisms.py` accepts no source/plan arguments and renders only fixed
repository source/data. It checks a 16-second/480-frame 1080p draft plus both theme previews,
continuous clip metadata, full decoding and standalone project export. The fixture is silent
and uses explicitly estimated timing; it is not native inference, new TTS/image inference,
Docker deployment or human playback/listening acceptance.

Backend regressions cover global IDs, request identity, code line bounds, measured tail
budgets/locked/strict constraints, parameter references/ranges, integrated-stock invariants,
unused/hidden/unrelated assets and mandatory per-binding review. Browser coverage includes
numeric editing that changes actual SVG state and survives a revision save. CI runs the
new fixed renderer and retains its verification/video evidence.

The delivery PR targets main and includes the previously stacked semantic/image work. Main
only gains those capabilities after that integration PR is merged; PRs merged into feature
branches alone do not update the default branch. Actual configured native/image/voice and
Docker/gVisor acceptance remains pending in this environment. See the task goal for execution.
