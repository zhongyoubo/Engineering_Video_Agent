# Fixed self-project introduction test

This is an authored showcase of this repository with real source ingestion, UI actions, Mandarin audio, measured word timing and Remotion rendering. It is **not** native-model inference, generated-source isolation acceptance, Whisper verification or listening certification.

Narration is restricted to exact excerpts of the already public README at `8973bcade2f342eda2a082024ff73c4904b722e5`. `prepare_audio.py` sends only those excerpts to Microsoft Edge read-aloud (Yunxi). It never sends the source ZIP, user uploads, credentials, logs or new/private narration. Changing the narration requires revisiting that external-service choice. TLS verification stays enabled; the optional host-configured CA is honored.

After normal bootstrap, install optional Edge support with `.venv/bin/python -m pip install -e 'apps/api[edge]'`. Configure a working Chromium through `CHROME_EXECUTABLE`. Stop any app occupying ports 5173/8000. Then:

```bash
.venv/bin/python examples/project-intro/prepare_input.py
.venv/bin/python examples/project-intro/capture_ui.py
.venv/bin/python examples/project-intro/prepare_audio.py
.venv/bin/python scripts/verify_project_intro.py --action build
.venv/bin/python scripts/verify_project_intro.py --action preview
# Inspect full-size frames and continuous clips; correct errors and repeat gates.
.venv/bin/python scripts/verify_project_intro.py --action final
.venv/bin/python scripts/verify_project_intro.py --action package
```

Outputs under `.verify-project-intro`: MP4, standalone Remotion project ZIP with local audio/font/UI assets, SRT, script, source evidence and verification JSON. The UI captures explicit **template + storyboard mode** so it can exercise source ingestion/editing without a configured model. It never executes uploaded code on the host. The separate video source is the fixed repository-authored `Video.tsx`, rendered only by this explicit verification script.

The output is 3840×2160 / 30fps. UI recording is a real 1920×1080 capture, enlarged in the 4K composition and played at 1.25×; its pixels are not claimed as native 4K. Other diagrams/text are vector/Remotion elements. Audio uses actual provider word boundaries, not equal-duration or Whisper-derived timing. The Qwen sentence quotes architecture documentation; the sample uses Edge, as the scene explicitly labels.

Each build, preview and final must have the same complete project fingerprint; package rejects stale artifacts. The API's production controller and no-host-fallback sandbox policy remain unchanged. Human playback/listening and real native-provider deployment are separate acceptance tasks.
