"""Actual native Agent + image gateway + isolated render acceptance. Consumes provider quota."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))


def main():
    from explainer.config import Settings
    from explainer.api import insert_revision
    from explainer.db import Database
    from explainer.domain import Brief
    from explainer.services.assets.image_service import configured
    from explainer.services.assets.registry import restore_assets
    from explainer.services.assets.usage import validate_generated_consumption
    from explainer.services.engineering.workspace import Workspace
    from explainer.storage import Storage
    from explainer.worker import run_once

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["codex", "claude-code"], required=True)
    parser.add_argument("--voice", choices=["qwen", "edge", "ming"], default="qwen")
    parser.add_argument(
        "--topic",
        default="用安排一顿晚饭的日常例子，介绍 AI Agent 怎样围绕目标行动、使用工具、按反馈调整，并在付款前等待确认。",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".verify-image-deployment/report.json"
    )
    args = parser.parse_args()
    settings = Settings().prepare()
    if (
        settings.scheduler != "local"
        or not configured(settings)
        or not shutil.which("docker")
    ):
        raise SystemExit(
            "Requires a dedicated local Worker, Docker/gVisor and a configured real image gateway; no fallback"
        )
    db = Database(settings.data_dir, settings.database_url)
    project, tenant = "image-acceptance-" + str(time.time_ns()), "local"
    db.execute(
        "INSERT INTO projects VALUES(?,?,?,?)",
        (project, tenant, "Image production acceptance", time.time()),
    )
    brief = Brief(
        title="Agent 如何把目标变成行动",
        prompt=args.topic
        + " 请通过 request_assets 的 image_service 生成至少一幅具体场景插画与一个真实透明的独立元素，"
        "使用 background_asset_key、AssetImage artwork 和带可见结果的实测旁白 transform 事件。"
        "保持素材生成来源在报告中，不要加入制作工具署名或演示提示。",
        target_seconds=45,
        video_mode="engineering",
        agent_engine=args.provider,
        quality_profile="professional",
        voice=args.voice,
    )
    request = insert_revision(db, settings, tenant, project, brief)
    run_once(settings, db, job_id=request["job_id"])
    job = db.one("SELECT * FROM jobs WHERE id=?", (request["job_id"],))
    if job["state"] != "SUCCEEDED":
        raise SystemExit("Actual image production failed: " + str(job["error"]))
    store = Storage(settings, db)
    saved = db.one(
        "SELECT asset_id FROM outputs WHERE revision_id=? AND role='engineering_state'",
        (request["revision_id"],),
    )
    _, path = store.get(tenant, saved["asset_id"])
    state = json.loads(path.read_text())
    generated = [
        v
        for v in state.get("generated_assets", {}).values()
        if v["request"]["provider"] == "image_service"
    ]
    if len(generated) < 2 or not any(
        v["has_alpha"] and v["request"]["transparent"] for v in generated
    ):
        raise SystemExit(
            "Acceptance requires actual registered image-service artwork and a real transparent cutout"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    w = Workspace(args.output.parent / "recovery-check")
    w.state = state
    restore_assets(
        w
    )  # Validates retained provider bytes, paths and previews; no new inference.
    board = json.loads(
        db.one(
            "SELECT storyboard FROM revisions WHERE id=?", (request["revision_id"],)
        )["storyboard"]
    )
    events = [
        e
        for s in board["scenes"]
        for e in s.get("compiled_semantic_events", [])
        if e["action"] == "transform"
    ]
    if not events or any(e["timing_source"] != "measured_words" for e in events):
        raise SystemExit("Acceptance requires actual measured narration transforms")
    bindings = validate_generated_consumption(
        board, state["generated_assets"], state.get("review")
    )
    report = dict(
        reviewed_asset_bindings=list(bindings),
        result="passed",
        revision_id=request["revision_id"],
        native_inference=True,
        configured_gateway_called=True,
        registered_image_count=len(generated),
        image_hashes=[
            hashlib.sha256(base64.b64decode(v["image_png"], validate=True)).hexdigest()
            for v in generated
        ],
        measured_transforms=len(events),
        human_playback_and_listening=False,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
