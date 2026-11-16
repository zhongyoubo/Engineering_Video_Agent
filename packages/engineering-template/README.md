# Editable Remotion project

Generated source lives in src/Video.tsx and optional src/scenes or src/components. Trusted Root.tsx supplies required CJK font, audio, captions and composition dimensions. props.json supplies actual compiled scene frames and authorized public media.

Install Node 20.19+, FFmpeg and a compatible Chrome. Run npm ci, npm run check, npm run preview, npm run render. Set CHROME_EXECUTABLE if needed. Use an isolated environment for model-generated source; never render untrusted projects on a workstation with credentials. The application runs this project in an isolated, no-network tool container.

Dependencies and lockfile are platform-controlled. Source, production plan, journal and visual review are included. Output is 1920x1080, 30fps. Review quality separately from successful compilation/decoding.
