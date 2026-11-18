# Project-owned illustrated production

## Contract

All production actions belong to the application: planning → registered material requests →
real word-timed voice → authored Remotion source → isolated build/preview/review/repair → final
render and source delivery. AI-generated artwork is an engineering dependency. A conversation
image tool or a separate postproduction script does not satisfy the application integration.

The implementation adds a configured HTTP image gateway, authenticated immutable project
image imports, retained PNG receipts and shared illustration/element composition. It does
not bundle model weights or assume that ChatGPT's image tool is an application API. The
native Agent still writes real TSX; arbitrary generated source runs only in the offline,
credential-free Docker/gVisor renderer. There is no new host fallback or topic keyword router.

## Providers and assets

| Provider | Input | Behavior |
|---|---|---|
| `component_svg` | typed title and rows | existing original code-drawn SVG document + companion preview |
| `image_service` | scene/subject prompt, purpose, size, transparency | Worker calls the configured real image gateway |
| `project_image` | ID from this project's authenticated catalog | imports the registered PNG without claiming new inference |

Agent planning and authoring receive catalog metadata plus actual bounded image previews.
Capabilities mean **configured**, not provider health or output quality certification.
The native action `request_assets` publishes the complete validated batch, updates platform
props and invalidates build/preview/review when bytes change. `inspect_asset` verifies actual
file and thumbnail hashes; image understanding still requires rendered-frame review.

`POST /api/v3/projects/{project_id}/images` accepts multipart `file` and `title`.
`GET` on the same route returns this project's catalog. Authentication and project ownership
are required. The Studio uploads the selected PNG files before it submits an engineering job.
IDs from another project or tenant fail in the trusted resolver, even if the caller knows them.
Catalog entries are immutable; changing an image creates a new ID. Binary content-addressed
storage precedes the catalog quota transaction, so a rejected insert may leave an unreferenced
stored object, never a catalog entry beyond the limit.

One imported/generated PNG: at most 12 MiB, 4096 px per side, 16,777,216 pixels, minimum 64 px
per side, single frame only. Metadata is removed through actual raster decoding and canonical
RGBA PNG encoding. A requested cutout must have transparent AND visible pixels. SVG factory
budget remains bounded separately; active project receipts permit 24 assets and 64 MiB of
actual image/preview bytes. Base64 checkpoint overhead is additional, still bounded by those
limits. Imported catalogs separately permit 24 images per project.

Receipts retain canonical bytes, request, model/service revision identity, actual dimensions,
transparency, content and thumbnail hashes, provenance and optional provider request ID.
Credentials and endpoint URLs are never included. Recovery validates the entire batch before
writing any files; generated PNGs are restored from retained bytes without paid re-inference.
A changed image provider model/revision/endpoint changes a subsequent request's cache key.
Idempotency keys are scoped to tenant/revision/request; the gateway must implement its own
idempotency semantics. A crash after a paid response but before fenced checkpoint persistence
can replay that request. This is not an exactly-once billing guarantee.

## Image gateway protocol: `eva-image-1`

Configure on the trusted Worker with `.env` (see `.env.example`):

```
EXPLAINER_IMAGE_SERVICE_URL=https://your-image-gateway.example/render
EXPLAINER_IMAGE_SERVICE_KEY=<administrator secret>
EXPLAINER_IMAGE_SERVICE_MODEL=<deployed model name>
EXPLAINER_IMAGE_SERVICE_REVISION=1
EXPLAINER_IMAGE_SERVICE_TIMEOUT=180
```

This is a small **project gateway protocol**, not a claim of native compatibility with any
vendor's image endpoint. A deployed gateway translates this contract to its model provider.
Its implementation/service credentials must be supplied by the deployment. Until then the
application advertises image_service=false and rejects that provider without substitution.
HTTPS is required except loopback HTTP for local gateways; authenticated URLs, query strings,
redirects and result URLs are rejected. The Agent cannot choose an endpoint or fetch a URL.

Request: POST the exact configured URL, Authorization Bearer secret and a scoped
Idempotency-Key header. JSON:

```json
{
  "protocol": "eva-image-1",
  "model": "your-deployed-model",
  "prompt": "A recognizable clay tomato, red body and green stem, isolated cutout, consistent soft side lighting; no text",
  "purpose": "A movable ingredient for a dinner-planning example",
  "size": "square",
  "transparent": true
}
```

Size values are landscape, portrait and square; the gateway resolves supported dimensions.
Return HTTP 200 with Content-Type application/json and exactly:

```json
{"png_base64":"<base64 of actual PNG bytes>","request_id":"optional-provider-request-id"}
```

Response parsing is streamed and bounded, redirects are not followed, errors exposed to the
Agent omit provider bodies/URLs/credentials. Cancellation/lease checks occur before the call,
while consuming chunks, after the response and before publication. A synchronous provider
request may continue until its configured network timeout; external billing is not rolled back.
The service adapter, key and network access never enter generated-code build/render containers.

## Composition and measured motion

`semantic_scene.background_asset_key` selects a full-frame cover illustration. Optional
`background_color`, `title_color` and `show_heading` control the shot presentation.
`AssetImage.image_style=artwork` displays unframed transparent/raster elements; the default
panel preserves existing document behavior. `image_fit` supports contain/cover. Initial
opacity, scale and rotation may be specified on entities.

A semantic `transform` event carries one or more destination fields: x, y, opacity, scale,
rotation. The existing real word-span resolver determines its start/end frames; the shared
protected renderer interpolates with smoothstep and holds the destination. A visible-result
expectation is required. Same-target changes cannot overlap, prerequisites must complete,
destinations must fit the logical stage and a held result frame must remain. Device-bound
entities support opacity changes only: moving their content independently would detach the
screen from its physical device. Scaling/rotation is about element center and may crop edges;
inspect actual frames. The stage is the existing 1720×650 region at (100,220), on a 1920×1080
logical canvas; the wrapper scales consistently to the requested output resolution.

Preview, final render, protected thumbnail, source export and revision hashing share this
renderer. Backgrounds and independent elements use registered keys, never arbitrary local
paths or URLs. The native review must still inspect every causal expectation in actual
before/during/after frames and continuous clips. Source and image-byte changes invalidate
prior gates. Removing an automatic illustrative EvidenceStack footer keeps provenance in
reports; explicit creator disclosures remain supported when the content requires one.

## Art direction

Choose concrete people, devices, places and everyday actions from the actual explanation;
use a coherent palette with suitable shot variation. Request scene backgrounds separately
from independently moving objects. Preserve empty regions for readable text. Illustrations
show a situation, semantic UI shows information/state, and motion shows what changes and why.
Do not turn every noun into a box, paste a fixed dinner template onto other subjects, put exact
UI text in generated images, or add unsolicited “素材/案例仅用于演示” banners. Exact text is
rendered by the project font. Report material sources and execution evidence outside the film.

## Verification boundaries

`test_production_assets.py` exercises actual PNG decoding/normalization, authenticated imports,
project isolation, controller dispatch, content hashes, recovery and measured transforms.
Gateway transport tests deliberately mock HTTP responses; they do not prove a deployed model.

`verify_production_assets.py --media-directory <fixed-fixture-media>` imports the hash-pinned
previous dinner artwork and Edge audio through this project's APIs/tools and renders the
reviewed fixed dispatcher using the protected Remotion project. It accepts neither arbitrary
TSX nor arbitrary plans. It proves real source compilation, illustration/element rendering,
word-timed motion, output decoding and source delivery. It does not prove new image inference,
native Agent inference, isolated deployment, full human playback or listening quality.

For actual integration acceptance on a configured dedicated Worker:

```bash
.venv/bin/python scripts/verify_image_production_deployment.py --provider codex --voice edge
```

This consumes native/image/voice provider quota and runs the real job pipeline. It requires
successful isolated rendering, retained real image-service artwork and an actual transparent
cutout plus measured transform events; merely configured services or a successful fixture
cannot make this check pass. Full human viewing/listening and unseen-topic quality remain
separate acceptance work. See goals/2026-11-18-production-assets.md for this session's evidence.
