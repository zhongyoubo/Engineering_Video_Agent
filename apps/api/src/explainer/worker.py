import argparse
import logging
import signal
import time

from .config import get_settings
from .db import Database, uid
from .services.pipeline import Pipeline


def run_once(settings, db, owner=None, job_id=None):
    job = db.claim(owner or uid("worker"), settings.lease_seconds, job_id)
    if not job:
        return False
    try:
        Pipeline(settings, db, job).run()
    except Exception:
        logging.exception("Job %s failed", job["id"])
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.scheduler != "local":
        raise SystemExit("Use python -m explainer.temporal_worker for Temporal mode")
    db, owner, stopped = Database(settings.data_dir, settings.database_url), uid("worker"), [False]
    signal.signal(signal.SIGTERM, lambda *_: stopped.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: stopped.__setitem__(0, True))
    while not stopped[0]:
        done = run_once(settings, db, owner)
        if args.once:
            break
        if not done:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
