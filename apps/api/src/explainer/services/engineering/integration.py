"""Pipeline integration: durable authoring state and tenant-scoped artifacts."""

import json
from pathlib import Path
import shutil
from fontTools.ttLib import TTFont

from ...db import encode
from .agent import NativeEngineeringAgent
from .controller import EngineeringController
from .tools import RenderTools
from .workspace import Workspace, EngineeringError, atomic_json


def check_font(board, font):
    if not font.is_file():
        raise EngineeringError("Required Chinese font is missing")
    text = "".join(s.title + s.subtitle + s.narration + "".join(s.bullets) for s in board.scenes)
    if "\ufffd" in text:
        raise EngineeringError("Text contains Unicode replacement characters")
    with TTFont(font) as face:
        cmap = face.getBestCmap()
    missing = sorted({ord(c) for c in text if not c.isspace() and ord(c) not in cmap})
    if missing:
        raise EngineeringError(
            "Required font has no glyphs for: " + ",".join(f"U+{c:04X}" for c in missing[:12])
        )


def professional_preflight(brief, settings):
    if brief.quality_profile != "professional":
        return
    if (
        brief.voice not in {"qwen", "edge", "ming"}
        or (brief.voice == "qwen" and not settings.tts_key)
        or (brief.voice == "ming" and not settings.ming_url)
    ):
        raise EngineeringError("正式成片需要已配置的 Qwen-TTS / Edge 云端 / Ming 本地旁白服务，不回退到开发音色。")
    if not settings.alignment_python or not Path(settings.alignment_model).is_file():
        raise EngineeringError("正式成片需要真实语音对齐，请配置语音环境与本地对齐模型。")


def build_engineering_video(pipeline, board, content, manifest, props, public, production_plan):
    p = pipeline
    w = Workspace(p.directory / "engineering")
    # Current job checkpoint first, then parent project as an editable starting point.
    current = p.db.one(
        "SELECT asset_id FROM outputs WHERE revision_id=? AND role='engineering_state'", (p.revision["id"],)
    )
    parent = (
        p.db.one(
            "SELECT asset_id FROM outputs WHERE revision_id=? AND role='engineering_state'",
            (p.revision["parent_id"],),
        )
        if p.revision.get("parent_id")
        else None
    )
    saved = current or parent
    if saved:
        _, path = p.store.get(p.tenant, saved["asset_id"])
        w.state = json.loads(path.read_text())
        if not current:
            w.state.update(
                iteration=0,
                build_hash=None,
                preview_hash=None,
                review_hash=None,
                review=None,
                frames=[],
                finished=False,
                journal=[],
            )
        for frame in w.state.get("frames", []):
            _, materialized = p.store.get(p.tenant, frame["asset_id"])
            destination = w.root / frame["name"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(materialized, destination)
    w.prepare(props, public)
    # A previous accepted source must still be reviewed if props/template changed.
    if any(w.state.get(k) != w.fingerprint() for k in ["build_hash", "preview_hash", "review_hash"]):
        w.state["finished"] = False

    def persist(workspace):
        p.guard()
        for frame in workspace.state["frames"]:
            if not frame.get("asset_id"):
                frame["asset_id"] = p.asset(workspace.root / frame["name"], "engineering-frame", "image/png")
        state = p.store.put(
            p.tenant,
            encode(workspace.state).encode(),
            "engineering-state",
            "engineering-state.json",
            "application/json",
        )
        preview_assets = None
        if workspace.state["frames"] and workspace.state["preview_hash"] == workspace.fingerprint():
            keyframe_index = p.store.put(
                p.tenant,
                encode(workspace.state["frames"]).encode(),
                "report",
                "keyframes.json",
                "application/json",
            )
            preview_assets = {
                "engineering_preview": workspace.state["frames"][0]["asset_id"],
                "keyframes": keyframe_index["id"],
            }
        with p.db.transaction() as connection:
            p.db.lock_job(connection, p.job["id"])
            row = connection.execute(
                "SELECT fence,lease_owner,state FROM jobs WHERE id=?", (p.job["id"],)
            ).fetchone()
            if row["fence"] != p.job["fence"] or row["lease_owner"] != p.job["lease_owner"]:
                from ..pipeline import LostLease

                raise LostLease()
            if row["state"] == "CANCEL_REQUESTED":
                from ..pipeline import Canceled

                raise Canceled()
            if row["state"] != "RUNNING":
                from ..pipeline import LostLease

                raise LostLease()
            if preview_assets:
                for role, asset_id in preview_assets.items():
                    connection.execute(
                        "INSERT INTO outputs VALUES(?,?,?) ON CONFLICT(revision_id,role) DO UPDATE SET asset_id=excluded.asset_id",
                        (p.revision["id"], role, asset_id),
                    )
            else:
                connection.execute(
                    "DELETE FROM outputs WHERE revision_id=? AND role IN ('engineering_preview','keyframes')",
                    (p.revision["id"],),
                )
            connection.execute(
                "INSERT INTO outputs VALUES(?,?,?) ON CONFLICT(revision_id,role) DO UPDATE SET asset_id=excluded.asset_id",
                (p.revision["id"], "engineering_state", state["id"]),
            )
        atomic_json(workspace.state_path, workspace.state)

    def emit(kind, payload):
        p.db.event(p.job, kind, payload)

    agent = NativeEngineeringAgent(p.settings, p.runner, content, p.brief, manifest, w.root / "agent", emit)
    tools = RenderTools(p.settings, p.runner)
    controller = EngineeringController(
        w, agent, tools, persist, emit, p.guard, p.settings.engineering_max_steps
    )
    result = controller.run(production_plan)
    archive = w.root / "remotion-project.zip"
    w.export(archive, production_plan)
    review = p.store.put(
        p.tenant, encode(w.state["review"]).encode(), "report", "visual-review.json", "application/json"
    )
    journal = p.store.put(
        p.tenant, encode(w.state["journal"]).encode(), "report", "authoring-journal.json", "application/json"
    )
    preview = p.asset(w.root / w.state["frames"][0]["name"], "cover", "image/png", "cover.png")
    return Path(result["video"]), {
        "engineering_project": p.asset(
            archive, "engineering-project", "application/zip", "remotion-project.zip"
        ),
        "visual_review": review["id"],
        "authoring_journal": journal["id"],
        "cover": preview,
    }
