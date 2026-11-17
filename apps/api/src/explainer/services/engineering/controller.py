"""Observe/repair loop with revision-specific build, preview and visual gates."""

import json
from .workspace import EngineeringError


class EngineeringController:
    def __init__(self, workspace, agent, tools, persist, emit, guard, max_steps=18):
        self.workspace, self.agent, self.tools = workspace, agent, tools
        self.persist, self.emit, self.guard, self.max_steps = persist, emit, guard, max_steps

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
        elif action.action == "build":
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
            accepted = (
                review["accepted"]
                and not review["issues"]
                and min(review["legibility"], review["visual_explanation"], review["timing"]) >= 4
                and (not motion_required or review["motion_continuity"] >= 4)
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
