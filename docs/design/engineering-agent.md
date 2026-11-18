# Engineering video Agent design — V3

## Objective
Given source code or a prompt, produce an editable Remotion project and narrated video through an engineering loop: understand, plan, author code, build, render keyframes, inspect, repair and deliver. Templates remain compatibility tools, not the core creative limit.

## Execution boundaries
The platform controls revisions, assets, leases and tool dispatch. The native Codex/Claude Agent supplies production plans and tool actions through a strict contract. It can author arbitrary React/TSX scene/component implementations within an allowed source tree; these are actual source files, not diagram-only JSON.

The native provider container may access its provider and read a sanitized source/context snapshot. Generated source is compiled and evaluated only in a different no-network, credential-free render container. No Docker socket or application files are mounted into either job container. The application Worker invokes Docker; it never imports or bundles generated source on host. JSON source-file writes are the mediated file-edit tool; native reasoning chooses subsequent build, preview, review, repair and finish actions.

## Lifecycle
Planning produces a typed production plan plus narration/storyboard. Existing Qwen/alignment and frame allocation compile the actual timing. Engineering then maintains a project workspace and durable journal. Native actions are write_files, build, render_preview, review and finish. Tools return concrete compiler diagnostics and sampled frame paths. Native review receives actual images. The system permits finish only after successful build, preview and accepted review bound to the identical current project hash. Every code/props/asset edit invalidates previous gates.

A controlled standalone project owns package dependencies, composition registration, font loading, audio and subtitles. Agent code exports the custom visual component and can add scene/component files. It cannot replace the trusted renderer, wrapper, dependency manifest or shell scripts. Invalid/unsupported file paths are rejected, never normalized into a different write target.

## State and recovery
The job lease/fence continues to guard committed checkpoints. The engineering workspace contains atomic state.json with source file contents, iteration, observations, hashes and review status. After every successful tool/Agent action it is uploaded as a tenant-scoped asset before the next action. A different Worker can materialize it. A job crash before a commit may replay a billable native invocation; no exactly-once claim is made. Repairs and native calls are bounded. Cancellation kills the Docker invocation and removes its container.

## Quality
Professional mode resolves auto voice to Qwen, requires real alignment and refuses development voice or silence. Draft is explicit and labelled. Generated projects require the bundled CJK font, UTF-8 text, no replacement characters, and font cmap coverage of narration/titles. Font failure aborts rendering. Preview samples each scene at several times; build, visual review and media decoding are separate evidence. A native review is not human certification. Exact wording and UI interactions still require review against supplied evidence.

## Interfaces and artifacts
Brief adds video_mode=engineering|template and quality_profile=professional|draft. The new /api/v3/videos endpoint defaults to engineering/Codex/professional; /api/v1/videos defaults preserve template compatibility; the new UI defaults to engineering with a selected native engine. Agent decisions and raw code are never executed by the browser editor. Engineering preview uses rendered images/MP4. Artifacts include production-plan.json, authoring-journal.json, visual-review.json, full Remotion source ZIP and the existing MP4/WAV/SRT/script/quality reports.

## Verification boundary
This workspace has no Docker daemon or native-provider credentials. Real compilation/rendering can be exercised only with authored trusted fixtures; native protocol and recovery are exercised with clearly labelled fakes. Real model quality, gVisor isolation, end-to-end provider cost and professional listening acceptance remain deployment checks.

## Interface references

Official native integration references checked 2026-10-30: https://developers.openai.com/codex/noninteractive/ and https://code.claude.com/docs/en/headless . Remotion tool API reference: https://www.remotion.dev/docs/renderer/render-still . CLI versions remain explicitly pinned in infra/native-agent/Dockerfile.

## Audience-purpose production contract

The product serves knowledge/technical creators through introduction, explanation,
analysis, viewpoint, advice and tutorial tasks. Subject, audience depth and visual form
are independent. New native creator planning resolves EditorialPlan.strategy from the
full context and records rationale, ordered scene coverage and success criteria. The
publication review additionally scores purpose_fulfillment against actual content.
See product/positioning-and-content-taxonomy.md (under docs) and content-strategy.md.
The engineering execution loop and isolation/evidence boundaries remain unchanged.

## Project-owned materials and illustration

The trusted Worker now mediates image generation through an explicitly configured gateway,
and resolves imported raster IDs against tenant AND project ownership. Image catalogs include
actual bounded previews for native planning. Asset requests, byte inspection, checkpoint
recovery and source export are application operations, not conversation-only helpers.
Protected shared scenes compose full-frame illustrations and measured independent-element
transforms while preserving the same source-hash and causal review gates. Provider secrets
stay outside generated code containers. The fixed host verifier remains an explicit reviewed
fixture only. See project-owned-visual-production.md for protocol, limits and actual acceptance.

## Reference-effect correction

The authoring loop retains its source and isolation boundaries. Production plans now enforce
project-wide material identity; native actions cannot silently replace a planned material with
a contradictory request. Measured event endings contribute to frame allocation before source
rendering. Every declared material binding requires explicit native frame review. Shared
protected theme/code/mechanism modules support parameter-linked diagrams without topic routing.
See reference-production-corrections.md for precise implemented paths and limits.
