"""Package tracked text from this public repository for the self-ingestion test."""

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / ".verify-project-intro"
out.mkdir(exist_ok=True)
suffixes = {
    ".py",
    ".tsx",
    ".ts",
    ".md",
    ".json",
    ".mjs",
    ".yml",
    ".yaml",
    ".css",
    ".html",
    ".toml",
    ".txt",
}
paths = (
    subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
)
with zipfile.ZipFile(out / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in paths:
        path = ROOT / name
        if (
            path.is_file()
            and path.suffix in suffixes
            and not name.startswith("examples/generated/")
        ):
            archive.write(path, name)
manifest = {
    "git_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "working_changes_included": True,
    "source_zip_sha256": hashlib.sha256((out / "source.zip").read_bytes()).hexdigest(),
}
(out / "source-manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
