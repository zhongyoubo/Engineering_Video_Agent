import json
import sqlite3
import time
import uuid
from contextlib import contextmanager


def uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


SCHEMA_SQL = """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
            INSERT INTO schema_version VALUES(1) ON CONFLICT(version) DO NOTHING;
            CREATE TABLE IF NOT EXISTS projects(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, name TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS inputs(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project_id TEXT NOT NULL,
              asset_id TEXT NOT NULL, manifest TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project_id TEXT NOT NULL, parent_id TEXT,
              brief TEXT NOT NULL, content TEXT, storyboard TEXT, quality TEXT,
              version INTEGER NOT NULL DEFAULT 1, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, revision_id TEXT NOT NULL,
              state TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'queued', progress REAL NOT NULL DEFAULT 0,
              error TEXT, lease_owner TEXT, lease_until REAL, fence INTEGER NOT NULL DEFAULT 0,
              attempts INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoints(
              job_id TEXT NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(job_id,stage));
            CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, job_id TEXT NOT NULL,
              kind TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS assets(
              id TEXT PRIMARY KEY, tenant TEXT NOT NULL, hash TEXT NOT NULL, kind TEXT NOT NULL,
              filename TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, created REAL NOT NULL,
              UNIQUE(tenant,hash,kind,filename));
            CREATE TABLE IF NOT EXISTS outputs(
              revision_id TEXT NOT NULL, role TEXT NOT NULL, asset_id TEXT NOT NULL,
              PRIMARY KEY(revision_id,role));
            CREATE TABLE IF NOT EXISTS voice_cache(
              tenant TEXT NOT NULL, key TEXT NOT NULL, asset_id TEXT NOT NULL, duration REAL NOT NULL,
              engine TEXT NOT NULL, PRIMARY KEY(tenant,key));
            CREATE TABLE IF NOT EXISTS idempotency(
              tenant TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL, response TEXT NOT NULL,
              PRIMARY KEY(tenant,key));
            CREATE INDEX IF NOT EXISTS ix_jobs_claim ON jobs(state,lease_until,created);
            CREATE INDEX IF NOT EXISTS ix_projects_tenant ON projects(tenant,created);
            CREATE INDEX IF NOT EXISTS ix_events_job ON events(tenant,job_id,seq);
"""
SCHEMA_SQL += """
CREATE TABLE IF NOT EXISTS project_images(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project_id TEXT NOT NULL,
 asset_id TEXT NOT NULL, metadata TEXT NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_project_images ON project_images(tenant,project_id);
CREATE TABLE IF NOT EXISTS audio_timings(
 tenant TEXT NOT NULL,asset_id TEXT NOT NULL,method TEXT NOT NULL,payload TEXT NOT NULL,
 PRIMARY KEY(tenant,asset_id));
"""


class SQLiteDatabase:
    """Single-host durable queue. WAL + leases + fencing, not a distributed database."""

    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "studio.db"
        with self.connect() as c:
            c.executescript(SCHEMA_SQL)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=30000")
        c.execute("PRAGMA foreign_keys=ON")
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def transaction(self):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
                c.commit()
            except BaseException:
                c.rollback()
                raise

    def lock_tenant(self, conn, tenant):
        """SQLite BEGIN IMMEDIATE already serializes quota and idempotency checks."""

    def lock_job(self, conn, job_id):
        """BEGIN IMMEDIATE provides the SQLite write fence."""

    def one(self, sql, args=()):
        with self.connect() as c:
            row = c.execute(sql, args).fetchone()
            return dict(row) if row else None

    def all(self, sql, args=()):
        with self.connect() as c:
            return [dict(r) for r in c.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self.transaction() as c:
            return c.execute(sql, args).rowcount

    def event(self, job, kind, payload, conn=None):
        args = (job["tenant"], job["id"], kind, encode(payload), time.time())
        if conn:
            conn.execute("INSERT INTO events(tenant,job_id,kind,payload,created) VALUES(?,?,?,?,?)", args)
        else:
            self.execute("INSERT INTO events(tenant,job_id,kind,payload,created) VALUES(?,?,?,?,?)", args)

    def claim(self, owner, lease_seconds, job_id=None):
        now = time.time()
        with self.transaction() as c:
            c.execute(
                "UPDATE jobs SET state='FAILED',error='任务恢复次数超过限制',updated=? "
                "WHERE state='RUNNING' AND lease_until<? AND attempts>=4",
                (now, now),
            )
            # Requested cancellations with no live worker are finalized by the queue itself.
            c.execute(
                "UPDATE jobs SET state='CANCELED',updated=? WHERE state='CANCEL_REQUESTED' "
                "AND (lease_until IS NULL OR lease_until<?)",
                (now, now),
            )
            query = (
                "SELECT * FROM jobs WHERE (state='QUEUED' OR (state='RUNNING' AND lease_until<?)) "
                "AND attempts<4"
            )
            args = [now]
            if job_id:
                query += " AND id=?"
                args.append(job_id)
            row = c.execute(query + " ORDER BY created LIMIT 1", args).fetchone()
            if not row:
                return None
            c.execute(
                "UPDATE jobs SET state='RUNNING',lease_owner=?,lease_until=?,fence=fence+1,"
                "attempts=attempts+1,updated=? WHERE id=?",
                (owner, now + lease_seconds, now, row["id"]),
            )
            job = dict(c.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())
            self.event(job, "job.started", {"attempt": job["attempts"]}, c)
            return job

    def heartbeat(self, job, seconds):
        return self.execute(
            "UPDATE jobs SET lease_until=?,updated=? WHERE id=? AND fence=? "
            "AND lease_owner=? AND state IN ('RUNNING','CANCEL_REQUESTED')",
            (time.time() + seconds, time.time(), job["id"], job["fence"], job["lease_owner"]),
        )

    def release_stage(self, job):
        with self.transaction() as c:
            self.lock_job(c, job["id"])
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if (
                not row
                or row["state"] not in {"RUNNING", "CANCEL_REQUESTED"}
                or row["fence"] != job["fence"]
                or row["lease_owner"] != job["lease_owner"]
            ):
                return False
            state = "CANCELED" if row["state"] == "CANCEL_REQUESTED" else "QUEUED"
            c.execute(
                "UPDATE jobs SET state=?,lease_owner=NULL,lease_until=NULL,attempts=attempts-1,updated=? WHERE id=?",
                (state, time.time(), job["id"]),
            )
            return True

    def finish(self, job, state, error=None):
        with self.transaction() as c:
            self.lock_job(c, job["id"])
            current = c.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if (
                not current
                or current["state"] not in {"RUNNING", "CANCEL_REQUESTED"}
                or current["fence"] != job["fence"]
                or current["lease_owner"] != job["lease_owner"]
            ):
                return False
            if current["state"] == "CANCEL_REQUESTED":
                state = "CANCELED"
            c.execute(
                "UPDATE jobs SET state=?,error=?,progress=?,lease_until=NULL,lease_owner=NULL,updated=? "
                "WHERE id=?",
                (
                    state,
                    error,
                    1 if state in {"SUCCEEDED", "PARTIAL"} else current["progress"],
                    time.time(),
                    job["id"],
                ),
            )
            self.event(job, "job.completed", {"state": state, "error": error}, c)
            return True


def Database(directory, url=""):
    if url:
        from .postgres import PostgresDatabase

        return PostgresDatabase(directory, url)
    return SQLiteDatabase(directory)
