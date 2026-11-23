"""Real provider -> generated TSX -> isolated rendering acceptance. Consumes API quota."""

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from explainer.config import Settings
    from explainer.db import Database
    from explainer.domain import Brief
    from explainer.api import insert_revision
    from explainer.worker import run_once
    from explainer.adapters.native_agent import capability
    from explainer.storage import Storage

    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["codex", "claude-code"], required=True)
    parser.add_argument("--draft", action="store_true")
    parser.add_argument(
        "--topic",
        default="用不同的视觉表达，直观解释内容策划、动画工程、配音对齐与渲染验证。",
    )
    parser.add_argument(
        "--creative",
        action="store_true",
        help="Require original reusable source artwork and current creative review",
    )
    parser.add_argument(
        "--expect-technique",
        choices=["svg", "canvas", "three", "images", "screen", "diagram"],
        action="append",
        default=[],
    )
    parser.add_argument("--output", default="engineering-deployment-verification.json")
    args = parser.parse_args()
    settings = Settings().prepare()
    if settings.scheduler != "local":
        raise SystemExit("Use a dedicated local scheduler acceptance environment")
    ready = capability(settings, args.provider)
    if not ready["ready"]:
        report = {
            "result": "blocked",
            "provider": args.provider,
            "creative_requested": args.creative,
            "docker_available": ready["docker_available"],
            "credential_configured": ready["credential_configured"],
            "provider_enabled": ready["enabled"],
            "actual_native_inference": False,
            "reason": "Requires configured native provider and isolated renderer; no host or fixed-fixture fallback",
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        raise SystemExit(2)
    db = Database(settings.data_dir, settings.database_url)
    project = "engineering-acceptance-" + str(time.time_ns())
    db.execute(
        "INSERT INTO projects VALUES(?,?,?,?)",
        (project, "local", "Engineering acceptance", time.time()),
    )
    brief = Brief(
        title="从想法到视频工程",
        prompt=args.topic
        + (
            " 为本主题原创可识别的源码素材，存放在src/assets；自主设计场景、配色和因果动效。不要把所有对象变成框图。"
            if args.creative
            else ""
        )
        + (
            " 本次需要使用的创作技术：" + ",".join(args.expect_technique)
            if args.expect_technique
            else ""
        ),
        target_seconds=30,
        video_mode="engineering",
        agent_engine=args.provider,
        quality_profile="draft" if args.draft else "professional",
        voice="none" if args.draft else "qwen",
    )
    r = insert_revision(db, settings, "local", project, brief)
    run_once(settings, db, job_id=r["job_id"])
    job = db.one("SELECT * FROM jobs WHERE id=?", (r["job_id"],))
    if job["state"] != "SUCCEEDED":
        raise SystemExit("Engineering acceptance failed: " + str(job["error"]))
    roles = {
        x["role"]
        for x in db.all(
            "SELECT role FROM outputs WHERE revision_id=?", (r["revision_id"],)
        )
    }
    assert {
        "video",
        "engineering_project",
        "visual_review",
        "authoring_journal",
        "production_plan",
    } <= roles
    creative = None
    if args.creative:
        store = Storage(settings, db)
        output = db.one(
            "SELECT asset_id FROM outputs WHERE revision_id=? AND role='engineering_project'",
            (r["revision_id"],),
        )
        _, archive = store.get("local", output["asset_id"])
        with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as z:
            creative = json.loads(z.read("creative-manifest.json"))
            review = json.loads(z.read("visual-review.json"))
            assert creative["scenes"] and any(
                p.startswith("src/assets/") for p in creative["source_assets"]
            )
            for path, digest in creative["source_assets"].items():
                assert hashlib.sha256(z.read(path)).hexdigest() == digest
            required = {
                s["scene_id"] + ":" + kind + ":" + e["id"]
                for s in creative["scenes"]
                for kind, field in [("element", "elements"), ("event", "events")]
                for e in s[field]
            }
            assert (
                review["accepted"] and set(review["creation_expectations"]) == required
            )
            assert (
                min(
                    review[k]
                    for k in [
                        "subject_fidelity",
                        "scene_composition",
                        "creative_motion",
                    ]
                )
                >= 4
            )
            techniques = {t for s in creative["scenes"] for t in s["techniques"]}
            assert set(args.expect_technique) <= techniques
            events = [e for s in creative["scenes"] for e in s["compiled_events"]]
            assert events, "Creative acceptance requires actual causal motion"
            if not args.draft:
                assert all(e["timing_source"] == "measured_words" for e in events)
    report = {
        "result": "passed",
        "actual_native_inference": True,
        "isolated_generated_code": True,
        "provider": args.provider,
        "draft": args.draft,
        "revision_id": r["revision_id"],
        "human_quality_acceptance": False,
        "creative_source_assets": creative["source_assets"] if creative else None,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
