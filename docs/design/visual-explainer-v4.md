# Visual explainer V4 — implemented contracts and operation

The upgrade keeps the V3 mediated TSX authoring loop, source/props/assets hash gates, no-credential offline rendering and tenant-scoped durable jobs. It adds visual explanatory building blocks; it is not a claim of automatic human-quality parity with reference videos.

## Content to visual explanation

Planning now accepts `scene.motion`: a purpose, chapter label, pattern, stable element IDs and narration-anchored events. Patterns are overview, code_scan, compare, graph, capacity, queue and depth. They represent different explanatory relationships, not keyword routing. Free TSX remains supported.

`src/motion-kit.tsx` is a platform-owned library copied into every standalone engineering project. It exports `MotionScene`, `motionProgress`, and the editorial_warm/workspace_tech design packs. Agent code may compose or replace visual treatments within its own files; it cannot modify the protected library or trusted renderer. Only React/Remotion/SVG/CSS are needed; no runtime dependency installation or remote assets.

`MotionEvent` references an element and a phrase/occurrence/start-or-end/offset. After actual speech alignment and frame allocation, `compile_motion` resolves phrases against the supplied transcript and measured spans. Missing phrases, unknown targets, unsupported duplicate target/actions and out-of-budget events are rejected. Draft timing can be estimated, with an explicit label. Professional motion requires measured timing. A merged Chinese token span retains its measured boundary rather than inventing character-level precision.

Scene/chapter metadata supports grouping; planning currently has a bounded maximum of 32 scenes. It is not yet a separate hierarchical chapter planner. Motion edit controls are intentionally limited to labels, pattern, purpose, anchor phrases and offsets; they are not a full nonlinear video editor. Event insertion uses a stable element ID and is saved as a new revision.

## Output profiles

`Brief.render_profile` supports 1080p and 4k at 30fps. API validation rejects mismatched aspect ratios. Root renders a 1920x1080 logical canvas into the selected composition size, so text and vector graphics are rasterized at final resolution. Agent code must not double-scale. Raster captures still need sufficient source resolution.

Both engineering and compatibility renderer paths use selected dimensions. Media validation checks dimensions, frame count and frame rate. Preview pixel checks use the actual expected size. The supported fps remains explicitly 30; configurable arbitrary frame rates and vertical reflow are future work.

Rebuild the existing engineering-render Docker image after pulling. Otherwise its platform-owned render.mjs will not match the upgraded protocol/props. Allow a suitable `EXPLAINER_ENGINEERING_TOOL_TIMEOUT` for 4K jobs (default 900s; maximum 7200s). Container resource sizing and real isolated 4K acceptance must be benchmarked in the target environment.

## Voice identity and truthful fallback

VoiceSpec contains voice_id, model, speed and revision. The effective configuration and service revision are part of the audio cache key, along with text, language and mastering version. Changing Edge voice, Ming endpoint/model, speed or service revision invalidates cached speech. Forks clear scene audio and motion timing when narration, language, engine or VoiceSpec changes. Old/unknown audio cannot satisfy a new professional request.

Qwen defaults to the service's configured professional-male reference. This clone service does not support arbitrary per-request voice/model selection; unsupported requests are rejected. Operators must change EXPLAINER_TTS_REVISION whenever the actual model/reference configuration changes. Ming's current adapter exposes model but not arbitrary voice selection. Edge uses edge_tts and is not a guaranteed Azure Speech service. Naturalness and professional pronunciation are listening criteria, not provider-name guarantees.

Speed is applied before final alignment. Existing highpass/loudnorm processing is preserved. Actual PCM waveform/peak/RMS measurements are exported; they are explicitly not LUFS, true-peak, pronunciation or listening certification. Silent professional narration is rejected. Real alignment still uses the existing local stable-ts adapter; remote alignment provider support is not claimed.

## Continuous previews and review

`preview` renders three keyframes per scene, a continuous 720p clip of up to four seconds near the first semantic event, and a chronological 4x2 contact sheet sampled at 2fps. All artifacts are versioned and persisted for recovery. These windows are representative, not coverage of every event or all scene boundaries.

Review must name every current ordinary keyframe and every motion sheet, and score motion continuity. Source/props/assets changes clear build, preview, clips and review gates. Browser playback of the actual clips is available in Studio; raw generated JavaScript is not evaluated in the application origin. The model receives contact sheets, not a claim that it watched/heard the complete MP4. The current reviewer remains the native authoring engine; independent reviewer routing and full listening certification remain deployment/further work.

`motion_previews` is an index of tenant-scoped assets per scene. `motion_preview` is the first ready clip for the main preview pane. `audio_analysis` contains real waveform peaks and amplitude measurements. `compare` returns scene field and brief changes only within the same tenant and project; it does not prove pixel invariance of locked scenes.

Actual runtime insertion updates and revalidates the effective production plan. The compiled plan is checkpointed with timeline state, so recovery uses the same scene list and actual props. User-provided captures remain distinguished from actual observed runs.

## MCP deployment

The optional server uses the official Python MCP SDK, pinned to 1.26.0, and stdio transport. It is an API client; it neither runs generated code nor receives supplier model keys. Install in a separate environment if desired:

```bash
python -m venv .mcp-venv
.mcp-venv/bin/python -m pip install -e 'apps/api[mcp]'
```

Configure the client command to that environment's Python with arguments `-m explainer.mcp_server`, and environment variables EXPLAINER_MCP_URL (default http://127.0.0.1:8000) and EXPLAINER_MCP_TOKEN (the appropriate tenant API access key). Keep the API and Worker running. Tools:

| Tool | Behavior |
|---|---|
| video_get_capabilities | Read actual configuration/capabilities |
| video_create_project | Create tenant-owned project |
| video_create_job | POST v3 engineering request, return asynchronous job ID |
| video_get_job | Read persisted status |
| video_get_artifacts | Read revision and artifact IDs |
| video_cancel_job | Request existing cancellation workflow |
| video_fork_revision | Preserve original, save edits as new revision |

No source/URL-derived arbitrary shell, redirects or resource path injection is exposed. API tenant checks and active-job quotas remain authoritative. Artifact bytes are fetched through the authenticated asset API, not embedded as huge tool responses. This first bridge does not yet expose automatic source uploads, a registry of third-party servers or per-user OAuth.

Pass an `idempotency_key` when calling video_create_job to safely repeat a submission. Forks use expected_version for optimistic concurrency; they always create a new revision.

`scripts/verify_mcp.py` performs real SDK initialization, tool discovery and authenticated API create/read/cancel calls. It does not invoke a model. Remotion's former hosted documentation MCP is no longer used; external official skills and future providers must be trusted/versioned separately.

## Verification and remaining acceptance

Routine: `.venv/bin/python scripts/check.py`; `CHROME_EXECUTABLE=/path/to/chrome npm run test:ui`; `npm run format:check`.

Fixed trusted fixtures: `scripts/verify_visual_v4.py` and the existing pipeline fixture script. These are reviewed repository inputs and not a host fallback for arbitrary user/model code. The V4 fixture builds/renders three silent drafts (code scan, depth, queue), checks 4K decoding, frame dimensions, continuous previews and source export. It does not synthesize new audio or use real native inference.

For full acceptance run the existing real-provider deployment script separately for Codex and Claude with configured isolated Worker, TTS and alignment. Review a newly narrated 30–60 second sample, then a mixed UI/diagram full video. Record full playback/listening and independent quality review separately. Never mark those checks passed from a codec test or fixture self-score.
