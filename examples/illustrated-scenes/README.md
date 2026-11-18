# Illustrated Agent fixture

Fixed repository-owned source/storyboard. Media is the existing dinner-example delivery:
`assets/{kitchen,ingredients,recipe,grocery,phone,meal,tomato,greens}.png` and
`voice/{opening,goal,ingredients,tools,feedback,approval,result,closing}.{wav,json}`.
All required bytes are pinned in media.manifest.json. Media is not bundled into Git.

```
npm ci
npx remotion browser ensure
CHROME_EXECUTABLE=/path/to/chrome-headless-shell .venv/bin/python scripts/verify_production_assets.py --media-directory /path/to/dinner-media
```

The verifier uses project-scoped authenticated image import and mediated asset actions,
actual Edge word times and the shared Remotion renderer. It delivers an MP4, causal sampled
previews, verification.json and Agent_Remotion_Project.zip under .verify-production-assets.
It is a fixed reviewed host verifier only; arbitrary generated code still requires isolation.
No image/native inference or new voice generation is claimed. For actual configured pipeline
acceptance use scripts/verify_image_production_deployment.py. See the design document.
