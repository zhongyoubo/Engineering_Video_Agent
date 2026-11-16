"""Download pinned speech weights; verify official content hashes before use.
Run in the speech environment. Models are intentionally excluded from delivery.
"""

import argparse, hashlib, json, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import HfApi, hf_hub_url

parser = argparse.ArgumentParser()
parser.add_argument("--output", default=".models")
args = parser.parse_args()
root = Path(args.output)
root.mkdir(parents=True, exist_ok=True)
repo = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
revision = "5d83992436eae1d760afd27aff78a71d676296fc"
info = HfApi().model_info(repo, revision=revision, files_metadata=True)


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def transfer(url, path, size, sha):
    path.parent.mkdir(parents=True, exist_ok=True)
    if (
        path.exists()
        and path.stat().st_size == size
        and (not sha or digest(path) == sha)
    ):
        return
    temp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as source, temp.open("wb") as target:
        while block := source.read(4 * 1024 * 1024):
            target.write(block)
    if temp.stat().st_size != size or (sha and digest(temp) != sha):
        raise RuntimeError("Integrity failure: " + path.name)
    temp.replace(path)
    print("Verified", path, flush=True)


def get(f):
    transfer(
        hf_hub_url(repo, f.rfilename, revision=revision),
        root / "qwen-base" / f.rfilename,
        f.size,
        f.lfs.sha256 if f.lfs else None,
    )


files = [
    f for f in info.siblings if f.rfilename.endswith((".json", ".txt", ".safetensors"))
]
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(get, files))
(root / "qwen-base/origin.json").write_text(
    json.dumps(dict(repo=repo, revision=revision))
)
sha = "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9"
transfer(
    f"https://openaipublic.azureedge.net/main/whisper/models/{sha}/tiny.pt",
    root / "tiny.pt",
    75572083,
    sha,
)
