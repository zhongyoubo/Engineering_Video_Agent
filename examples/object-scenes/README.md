# Object scene examples

hdmi.json is a fixed authored data fixture with eight concrete scenes, named device
ports, cables, distinct signal channels, state changes, narration anchors and optional
quiet original Foley. It is not a native Agent response or a hardware experiment.

The renderer draws actual vector device silhouettes and frame-driven state changes.
Picture/VRR/HDR motion and sound waves are explanatory illustrations, not measured
120Hz/HDR output, electrical waveforms or actual speaker recordings.

Run `CHROME_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/verify_object_scenes.py`
for fixed 9-second object/state/Foley checks in both rendering paths and an eleven-object
gallery. This script deliberately does not accept arbitrary source/TSX paths. Its draft
estimated timing is not speech alignment. Source rules and details: docs/design/object-scenes.md.
