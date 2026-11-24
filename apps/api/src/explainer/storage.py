import hashlib
import os
import time
from pathlib import Path

from .db import uid


class Storage:
    def __init__(self, settings, db):
        self.root = settings.data_dir / "objects"
        self.db = db
        self.settings = settings
        self.s3 = None
        if settings.storage_backend == "s3":
            import boto3
            from botocore.config import Config

            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint or None,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key or None,
                aws_secret_access_key=settings.s3_secret_key or None,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    connect_timeout=10,
                    read_timeout=60,
                    retries={"max_attempts": 3},
                ),
            )

    def key(self, tenant, digest):
        return f"objects/{tenant}/{digest[:2]}/{digest}"

    def put(self, tenant, content: bytes, kind, filename, mime):
        digest = hashlib.sha256(content).hexdigest()
        directory = self.root / tenant / digest[:2]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / digest
        if self.s3:
            self.s3.put_object(
                Bucket=self.settings.s3_bucket,
                Key=self.key(tenant, digest),
                Body=content,
                ContentType=mime,
                Metadata={"sha256": digest},
            )
        if not path.exists():
            temporary = path.with_name(digest + "." + uid("tmp"))
            try:
                with temporary.open("xb") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                try:
                    os.replace(temporary, path)
                except PermissionError:
                    # Windows can refuse replacement while another writer's published object is open.
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        raise
            finally:
                temporary.unlink(missing_ok=True)
        with self.db.transaction() as c:
            c.execute(
                "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(tenant,hash,kind,filename) DO NOTHING",
                (uid("ast"), tenant, digest, kind, Path(filename).name, mime, len(content), time.time()),
            )
            row = c.execute(
                "SELECT * FROM assets WHERE tenant=? AND hash=? AND kind=? AND filename=?",
                (tenant, digest, kind, Path(filename).name),
            ).fetchone()
            return dict(row)

    def get(self, tenant, asset_id):
        asset = self.db.one("SELECT * FROM assets WHERE id=? AND tenant=?", (asset_id, tenant))
        if not asset:
            raise KeyError("Asset not found")
        path = self.root / tenant / asset["hash"][:2] / asset["hash"]
        if self.s3 and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + "." + uid("download"))
            try:
                self.s3.download_file(
                    self.settings.s3_bucket, self.key(tenant, asset["hash"]), str(temporary)
                )
                if hashlib.sha256(temporary.read_bytes()).hexdigest() != asset["hash"]:
                    raise ValueError("S3 asset checksum mismatch")
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        if not path.is_file():
            raise FileNotFoundError("Asset missing on disk")
        return asset, path

    def output(self, revision_id, role, asset_id):
        self.db.execute(
            "INSERT INTO outputs VALUES(?,?,?) ON CONFLICT(revision_id,role) DO UPDATE SET asset_id=excluded.asset_id",
            (revision_id, role, asset_id),
        )
