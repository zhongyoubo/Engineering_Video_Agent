"""Download ONLY pinned, reviewed upstream files. Optional development tool; no source execution."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "assets/library/packs"
SOURCES = {
    "phosphor": (
        "phosphor-icons/core",
        "2b75f3ad12b420c9504ef05df8d2564a28f8500e",
        [
            "LICENSE",
            *[
                f"assets/duotone/{name}-duotone.svg"
                for name in (
                    "book-open",
                    "brain",
                    "robot",
                    "terminal",
                    "folder",
                    "magnifying-glass",
                    "gear",
                    "monitor",
                )
            ],
        ],
    ),
    "soft3d": (
        "realvjy/3dicons",
        "8884d59e68a7bae0e0e2163af5b6c2ad992c01c8",
        [
            "LICENSE",
            "static/notebook-dynamic-00.png",
            "static/heart.png",
            "static/bubble.png",
        ],
    ),
    "motion": (
        "lifeprompt-team/remotion-scenes",
        "02c7a84241da7010b5f59c420b0110aafd1d6f0d",
        [
            "LICENSE",
            "src/scenes/TextAnimations/TextTypewriter.tsx",
            "src/scenes/TextAnimations/TextKinetic.tsx",
        ],
    ),
    "avocado": (
        "KhronosGroup/glTF-Sample-Assets",
        "e124e8d8d7330a5372bc2b4d00d39a4a9d7997ea",
        [
            "Models/Avocado/LICENSE.md",
            "Models/Avocado/README.md",
            "Models/Avocado/glTF-Binary/Avocado.glb",
            "Models/Avocado/screenshot/screenshot.jpg",
        ],
    ),
}


def download(spec):
    pack, repo, revision, name = spec
    url = f"https://raw.githubusercontent.com/{repo}/{revision}/{name}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024:
        raise ValueError("Pinned source exceeds byte budget")
    return pack, repo, revision, name, data


def main():
    specs = [
        (pack, repo, revision, name)
        for pack, (repo, revision, files) in SOURCES.items()
        for name in files
    ]
    with ThreadPoolExecutor(max_workers=5) as pool:
        staged = list(pool.map(download, specs))
    records = []
    for pack, repo, revision, name, data in staged:
        target = PACKS / pack / "upstream" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append(
            dict(
                pack=pack,
                repo=repo,
                revision=revision,
                path=name,
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
            )
        )
    (PACKS / "upstream-sources.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Pinned upstream source files saved: {len(records)}")


if __name__ == "__main__":
    main()
