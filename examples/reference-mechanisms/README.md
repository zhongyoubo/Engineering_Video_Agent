# Fixed parameter, flow and code verification

`CHROME_EXECUTABLE=/path/to/headless-shell .venv/bin/python scripts/verify_reference_mechanisms.py`

The script renders only this reviewed fixed dispatcher/storyboard. It produces a 16-second
1080p video, two theme previews, continuous clips, source project and verification JSON under
.verify-reference-mechanisms. Three shots demonstrate shared dial/tree/metric state, integrated
reservoir/queue state and source-line-24 paging/focus. No recorded reference assets are used.

No narration is generated: this is a silent draft with explicitly estimated anchors, not
native/image/TTS inference, Docker deployment or full human watching/listening acceptance.
Production generated code still requires the offline credential-free isolated Worker.
