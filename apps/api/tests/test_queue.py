import time

import pytest

from explainer.api import insert_revision
from explainer.domain import Brief
from explainer.services.pipeline import LostLease, Pipeline


def seed(settings, db):
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("p", "local", "p", time.time()))
    return insert_revision(db, settings, "local", "p", Brief(title="Test", prompt="Test", mode="storyboard"))


def test_claim_fencing(settings, db):
    seed(settings, db)
    a = db.claim("worker-a", 90)
    assert db.claim("worker-b", 90) is None
    db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (a["id"],))
    b = db.claim("worker-b", 90)
    assert b["fence"] > a["fence"]
    assert not db.finish(a, "SUCCEEDED")
    with pytest.raises(LostLease):
        Pipeline(settings, db, a).guard()
    assert db.finish(b, "SUCCEEDED")


def test_checkpoint_reused_after_crash(settings, db):
    seed(settings, db)
    first = db.claim("first", 90)
    p = Pipeline(settings, db, first)
    assert p.stage("unit", 0.1, lambda: {"value": 42})["value"] == 42
    db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (first["id"],))
    second = db.claim("second", 90)
    q = Pipeline(settings, db, second)
    assert q.stage("unit", 0.1, lambda: pytest.fail("must reuse checkpoint"))["value"] == 42


def test_cancel_wins_finish(settings, db):
    seed(settings, db)
    job = db.claim("owner", 90)
    db.execute("UPDATE jobs SET state='CANCEL_REQUESTED' WHERE id=?", (job["id"],))
    assert db.finish(job, "SUCCEEDED")
    assert db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "CANCELED"


def test_exhausted_crash_is_terminal(settings, db):
    seed(settings, db)
    job = db.claim("owner", 90)
    db.execute("UPDATE jobs SET attempts=4,lease_until=0 WHERE id=?", (job["id"],))
    assert db.claim("replacement", 90) is None
    assert db.one("SELECT state FROM jobs WHERE id=?", (job["id"],))["state"] == "FAILED"
