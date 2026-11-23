# Material pack review and corrections

Base: 85a7b23. Review recovery, staging, model lifecycle/validation, discovery performance,
preview correctness and export, while preserving tenant isolation and exact-hash gates.

Acceptance: reproduce concrete regressions; add focused tests without weakening the306-test
baseline; run scripts/check.py, configured test:ui, format/diff checks and the reviewed fixed
material renderer after model changes. No generated/user source host execution, native inference
or human audiovisual certification is implied.

## Progress

- Baseline scripts/check.py passed:306 backend tests, pure contracts, types and production build.
- Auditing authoritative material selection on resume, manifest recovery and repeated full-pack scans.

## Reproduction and delivery

Before fixes,8 regression cases failed. Fixed resume-selection loss, recovery overwriting
of pack identity, late symlink rejection after partial writes, malformed GLB integer ranges,
repeated catalog scans and browser stale/clipboard failures. Added same-version drift and
single-receipt scan coverage (10 new backend cases total), model commit/cleanup/draw error
handling and4K dpr. A production-rendered StrictMode wrapper alone did not reproduce dev
React effect replay; cleanup strengthening is distinct from the reproduced backend failures.

Final commands: scripts/check.py316 passed plus contracts/types/production build; configured
test:ui17 passed; format:check, verifier Ruff and diff checks passed. Fixed material verifier
compiled/rendered16s/480frames1080p30, checked nonempty model stills, decoded video and exported
licensed source. See docs/verification-material-packs.json for actual source/media hashes.
README/Roadmap and docs/design/material-pack-review-20261124.md updated. No native/image/TTS,
Docker deployment or human full viewing certification. Baseline assertions retained.
