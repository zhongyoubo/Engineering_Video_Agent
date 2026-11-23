# Editable Remotion project

Generated source lives in src/Video.tsx and optional src/scenes or src/components. Trusted Root.tsx supplies required CJK font, audio, captions and composition dimensions. props.json supplies actual compiled scene frames and authorized public media.

Install Node 20.19+, FFmpeg and a compatible Chrome. Run npm ci, npm run check, npm run preview, npm run render. Set CHROME_EXECUTABLE if needed. Use an isolated environment for model-generated source; never render untrusted projects on a workstation with credentials. The application runs this project in an isolated, no-network tool container.

Dependencies and lockfile are platform-controlled. Source, production plan, journal and visual review are included. Output is 1920x1080, 30fps. Review quality separately from successful compilation/decoding.

SpatialCity, QuantityMatrix and NodeNetwork compose through SceneRenderer with bounded
semantic_scene parameters and narration-anchored events. QuantityMatrix uses registered
bundled asset keys; repeated image tiles do not imply distinct source images. A single
immersive spatial entity uses show_heading=false and cannot cover a physical object stage.
neon_horizon is the third shared design pack. City rendering uses software WebGL (swangle),
Three 0.181.1, R3F 9.4.0 and matching Remotion 4.0.538. Preserve frame readiness and stable
geometry/identities. This vocabulary is not a general automatic 3D asset service.
