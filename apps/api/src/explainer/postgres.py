"""PostgreSQL repository using native upserts, row locks and SKIP LOCKED.

The query text is the shared, bound repository SQL. Only placeholder syntax is
adapted; DML conflict behavior is explicit SQL common to both engines.
"""

import threading
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .db import SCHEMA_SQL, SQLiteDatabase

_initialized = set()
_schema_lock = threading.Lock()


def placeholders(sql):
    result, quoted, i = [], None, 0
    while i < len(sql):
        char = sql[i]
        if quoted:
            result.append("%%" if char == "%" else char)
            if char == quoted:
                if i + 1 < len(sql) and sql[i + 1] == quoted:
                    result.append(sql[i + 1])
                    i += 1
                else:
                    quoted = None
        elif char in {"'", '"'}:
            quoted = char
            result.append(char)
        else:
            result.append("%s" if char == "?" else "%%" if char == "%" else char)
        i += 1
    return "".join(result)


class Row(dict):
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        value = self.cursor.fetchone()
        return Row(value) if value is not None else None

    def fetchall(self):
        return [Row(v) for v in self.cursor.fetchall()]


class Connection:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, args=()):
        return Cursor(self.raw.execute(placeholders(sql), args))


class PostgresDatabase(SQLiteDatabase):
    def __init__(self, directory, url):
        self.url = url
        self.path = None
        directory.mkdir(parents=True, exist_ok=True)
        with _schema_lock:
            if url not in _initialized:
                with self.transaction() as c:
                    c.execute("SELECT pg_advisory_xact_lock(619273901)")
                    schema = SCHEMA_SQL.replace(
                        "INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY"
                    ).replace(" REAL", " DOUBLE PRECISION")
                    for statement in schema.split(";"):
                        if statement.strip() and not statement.strip().startswith("PRAGMA"):
                            c.execute(statement)
                _initialized.add(url)

    @contextmanager
    def connect(self):
        with psycopg.connect(self.url, autocommit=True, row_factory=dict_row, connect_timeout=10) as raw:
            yield Connection(raw)

    @contextmanager
    def transaction(self):
        with self.connect() as c:
            with c.raw.transaction():
                yield c

    def lock_tenant(self, conn, tenant):
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(?,0))", (tenant,))

    def lock_job(self, conn, job_id):
        conn.execute("SELECT id FROM jobs WHERE id=? FOR UPDATE", (job_id,))

    def claim(self, owner, lease_seconds, job_id=None):
        with self.transaction() as c:
            now = float(c.execute("SELECT extract(epoch from clock_timestamp()) AS now").fetchone()["now"])
            c.execute(
                "UPDATE jobs SET state='FAILED',error='任务恢复次数超过限制',updated=? "
                "WHERE state='RUNNING' AND lease_until<? AND attempts>=4",
                (now, now),
            )
            c.execute(
                "UPDATE jobs SET state='CANCELED',updated=? WHERE state='CANCEL_REQUESTED' "
                "AND (lease_until IS NULL OR lease_until<?)",
                (now, now),
            )
            query = "SELECT * FROM jobs WHERE (state='QUEUED' OR (state='RUNNING' AND lease_until<?)) AND attempts<4"
            args = [now]
            if job_id:
                query += " AND id=?"
                args.append(job_id)
            row = c.execute(query + " ORDER BY created LIMIT 1 FOR UPDATE SKIP LOCKED", args).fetchone()
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
            "UPDATE jobs SET lease_until=extract(epoch from clock_timestamp())+?, "
            "updated=extract(epoch from clock_timestamp()) WHERE id=? AND fence=? AND lease_owner=? "
            "AND state IN ('RUNNING','CANCEL_REQUESTED')",
            (seconds, job["id"], job["fence"], job["lease_owner"]),
        )
