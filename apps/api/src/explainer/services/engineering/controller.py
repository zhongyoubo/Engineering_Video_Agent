"""Observe/repair loop with revision-specific build, preview and visual gates."""

import json
from .workspace import EngineeringError


class EngineeringController:
    def __init__(
        self, workspace, agent, tools, persist, emit, guard, max_steps=18, resolve_image=None, asset_scope=""
    ):
        self.workspace, self.agent, self.tools = workspace, agent, tools
        self.persist, self.emit, self.guard, self.max_steps = persist, emit, guard, max_steps
        self.resolve_image, self.asset_scope = resolve_image, asset_scope

    def run(self, plan):
        w = self.workspace
        if w.state.get("finished") and all(
            w.state.get(k) == w.fingerprint() for k in ["build_hash", "preview_hash", "review_hash"]
        ):
            result = self.tools.execute(w, "final")
            if result.get("ok"):
                return result
            w.state["finished"] = False
            w.state["build_hash"], w.state["preview_hash"], w.state["review_hash"] = None, None, None
            w.record("final.failed", result)
            self.persist(w)
        while w.state["iteration"] < self.max_steps:
            self.guard()
            try:
                action = self.agent.decide(w, plan)
            except ValueError:
                w.record(
                    "contract.rejected",
                    {
                        "diagnostic": "Native output did not satisfy the engineering action contract; return a complete valid action."
                    },
                )
                self.persist(w)
                continue
            try:
                self.apply(action)
            except (EngineeringError, ValueError) as error:
                w.record("rejected", {"action": action.action, "diagnostic": str(error)[:2000]})
            self.persist(w)
            if w.state["finished"]:
                self.guard()
                result = self.tools.execute(w, "final")
                if not result.get("ok"):
                    # A renderer failure re-enters repair, rather than returning success.
                    w.state["finished"] = False
                    w.state["build_hash"], w.state["preview_hash"], w.state["review_hash"] = None, None, None
                    w.record("final.failed", result)
                    self.persist(w)
                    continue
                return result
        raise EngineeringError("工程 Agent 已达到修复步数上限；未输出未经验证的成片。")

    def apply(self, action):
        w = self.workspace
        fingerprint = w.fingerprint()
        self.emit(
            "engineering.action",
            {"action": action.action, "step": w.state["iteration"], "summary": action.summary},
        )
        if action.action == "write_files":
            w.edit(action.files)
            w.record("files.written", {"paths": [e.path for e in action.files], "hash": w.fingerprint()})
        elif action.action == "request_assets":
            from ..assets.registry import request_assets

            receipts = request_assets(
                w,
                action.asset_requests,
                self.guard,
                getattr(self.tools, "settings", None),
                self.resolve_image,
                self.asset_scope,
            )
            w.record("assets.created", {"receipts": receipts})
        elif action.action == "inspect_asset":
            receipt = w.state.get("generated_assets", {}).get(action.asset_id)
            if not receipt:
                raise EngineeringError("No generated asset with this ID in this project")
            import hashlib

            path = w.project / "public" / receipt["filename"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
                raise EngineeringError("Asset bytes differ from receipt")
            preview = w.project / "public" / receipt["preview_filename"]
            if (
                not preview.is_file()
                or hashlib.sha256(preview.read_bytes()).hexdigest() != receipt["preview_sha256"]
            ):
                raise EngineeringError("Asset preview differs from receipt")
            from ..assets.registry import public_receipt

            w.record("asset.inspected", public_receipt(receipt))
        elif action.action == "build":
            props = json.loads((w.project / "props.json").read_text())
            for scene in props.get("scenes", []):
                background = (scene.get("semantic_scene") or {}).get("background_asset_key")
                if background and background not in w.state.get("generated_assets", {}):
                    raise EngineeringError("Request the background image before build")
                for entity in (scene.get("semantic_scene") or {}).get("entities", []):
                    if entity.get("asset_key") and entity["asset_key"] not in w.state.get(
                        "generated_assets", {}
                    ):
                        raise EngineeringError("Request the referenced generated asset before build")
            w.state["build_hash"], w.state["preview_hash"], w.state["review_hash"] = None, None, None
            w.state["frames"], w.state["review"] = [], None
            w.state["clips"], w.state["motion_frames"] = [], []
            result = self.tools.execute(w, "build")
            w.state["build_hash"] = fingerprint if result.get("ok") else None
            w.state["preview_hash"], w.state["review_hash"] = None, None
            w.record("build", result)
        elif action.action == "render_preview":
            if w.state["build_hash"] != fingerprint:
                raise EngineeringError("Build the current source before rendering keyframes")
            w.state["preview_hash"], w.state["review_hash"] = None, None
            w.state["frames"], w.state["review"] = [], None
            w.state["clips"], w.state["motion_frames"] = [], []
            result = self.tools.execute(w, "preview")
            w.state["preview_hash"] = fingerprint if result.get("ok") else None
            w.state["frames"] = result.get("frames", []) if result.get("ok") else []
            w.state["clips"] = result.get("clips", []) if result.get("ok") else []
            w.state["motion_frames"] = result.get("motion_frames", []) if result.get("ok") else []
            w.state["review_hash"] = None
            w.record("preview", result)
        elif action.action == "review":
            w.state["review_hash"] = None
            if w.state["preview_hash"] != fingerprint or not w.state["frames"]:
                raise EngineeringError("Review requires real keyframes of the current source")
            reviewed = set(action.review.inspected_frames)
            available = {f["name"] for f in w.state["frames"]}
            if reviewed != available:
                raise EngineeringError("Visual review must name every supplied sampled frame")
            review = action.review.model_dump()
            motion_required = json.loads((w.project / "props.json").read_text()).get(
                "motion_review_required", False
            )
            motion_available = {f["name"] for f in w.state.get("motion_frames", [])}
            if motion_required and (
                not w.state.get("clips")
                or not motion_available
                or set(review["inspected_motion_frames"]) != motion_available
            ):
                raise EngineeringError(
                    "Motion review requires current continuous previews and sampled motion sheets"
                )
            props = json.loads((w.project / "props.json").read_text())
            publication_required = props.get("presentation_profile") == "creator" and bool(props.get("cover"))
            strategy_required = publication_required and bool((props.get("editorial") or {}).get("strategy"))
            object_required = any(s.get("visual_scene") for s in props.get("scenes", []))
            if publication_required and not any(f.get("kind") == "thumbnail" for f in w.state["frames"]):
                raise EngineeringError("Publication review requires an independently rendered thumbnail")
            required_expectations = {
                scene["id"] + ":" + item["id"]
                for scene in props.get("scenes", [])
                for item in (scene.get("semantic_scene") or {}).get("expectations", [])
            }
            if required_expectations and (
                set(review["semantic_expectations"]) != required_expectations
                or review["semantic_accuracy"] < 4
            ):
                raise EngineeringError("Review must verify every causal semantic expectation")
            accepted = (
                review["accepted"]
                and not review["issues"]
                and min(review["legibility"], review["visual_explanation"], review["timing"]) >= 4
                and (not motion_required or review["motion_continuity"] >= 4)
                and (not strategy_required or review["purpose_fulfillment"] >= 4)
                and (not object_required or min(review["object_fidelity"], review["causal_motion"]) >= 4)
                and (
                    not publication_required
                    or min(
                        review["content_focus"],
                        review["cover_promise"],
                        review["opening_closing"],
                        review["viewer_presentation"],
                    )
                    >= 4
                )
            )
            w.state["review"] = {
                **review,
                "accepted": accepted,
                "project_hash": fingerprint,
                "reviewer": "native-agent; not human certification",
                "motion_evidence": "sampled contact sheets; not full playback/listening"
                if motion_required
                else "legacy keyframes",
            }
            w.state["review_hash"] = fingerprint if accepted else None
            w.record("review", w.state["review"])
        elif action.action == "finish":
            if not w.state["files"] or any(
                w.state[k] != fingerprint for k in ["build_hash", "preview_hash", "review_hash"]
            ):
                raise EngineeringError("Finish requires current source build, keyframes and accepted review")
            w.state["finished"] = True
            w.record("accepted", {"hash": fingerprint})
