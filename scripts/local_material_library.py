"""Register operator-owned PNGs in a separate, tenant-scoped local library."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.local_materials import (  # noqa: E402
    MAX_INDEX_BYTES, MAX_ITEMS, MATERIAL_ID, catalog, is_indirection, read_bounded, tenant_directory,
)
from explainer.services.assets.raster import MAX_IMAGE_BYTES, canonical_png  # noqa: E402


@contextmanager
def index_lock(directory):
    path = directory / "index.lock"
    if is_indirection(path):
        raise ValueError("Local material index lock cannot be redirected")
    with path.open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt

                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Another registration is updating the local material index") from exc
        yield


def write_atomic(path, content):
    fd, temporary = tempfile.mkstemp(prefix=path.name + "-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def add_material(root, directory, args):
    blob, _, _ = canonical_png(read_bounded(args.file, MAX_IMAGE_BYTES))
    directory.mkdir(parents=True, exist_ok=True)
    with index_lock(directory):
        items = catalog(root, args.tenant)
        if len(items) >= MAX_ITEMS or any(item["id"] == args.id for item in items):
            raise ValueError("Library is full or material ID already exists")
        digest = hashlib.sha256(blob).hexdigest()
        items.append(dict(id=args.id, title=args.title, origin=args.origin, rights=args.rights, sha256=digest))
        indexed = [{**item, "file": f"files/{item['sha256']}.png"} for item in items]
        content = json.dumps({"schema_version": 1, "items": indexed}, ensure_ascii=False, indent=2).encode("utf-8")
        if len(content) > MAX_INDEX_BYTES:
            raise ValueError("Registration would exceed the local material index byte budget")
        files = directory / "files"
        if is_indirection(files):
            raise ValueError("Local material file directory cannot be redirected")
        files.mkdir(exist_ok=True)
        path = files / f"{digest}.png"
        if path.exists() or is_indirection(path):
            if hashlib.sha256(read_bounded(path, MAX_IMAGE_BYTES)).hexdigest() != digest:
                raise ValueError("Existing content-addressed file is invalid")
        else:
            write_atomic(path, blob)
        write_atomic(directory / "index.json", content)
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=os.environ.get("EXPLAINER_LOCAL_MATERIAL_DIR"))
    parser.add_argument("--tenant", default="local")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    add = sub.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--origin", required=True)
    add.add_argument("--rights", required=True)
    add.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    if args.root is None or not args.root.is_absolute() or args.root.resolve().is_relative_to(ROOT.resolve()):
        parser.error("--root must be an absolute directory outside this repository")
    args.root = args.root.resolve()
    try:
        directory = tenant_directory(args.root, args.tenant)
        if args.command == "list":
            print(json.dumps(catalog(args.root, args.tenant), ensure_ascii=False, indent=2))
            return
        if not MATERIAL_ID.fullmatch(args.id) or any(
            not value.strip() or len(value) > limit
            for value, limit in ((args.title, 60), (args.origin, 300), (args.rights, 300))
        ):
            raise ValueError("Invalid ID, title, origin or rights")
        digest = add_material(args.root, directory, args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"id": args.id, "sha256": digest, "root": str(directory)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
