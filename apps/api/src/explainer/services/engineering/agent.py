"""Native planning and engineering actions. No template or model fallback."""

from ...adapters.native_agent import native_plan
from ...adapters.native_contract import validate_design
from ...config import ROOT
from ...specs import PATTERN_ELEMENT_LIMITS, PATTERN_LABEL_LIMITS
from .contracts import ProductionPlan, EngineeringAction, schema


class NativeEngineeringAgent:
    def __init__(self, settings, runner, content, brief, manifest, directory, emit):
        self.settings, self.runner, self.content, self.brief = settings, runner, content, brief
        self.manifest, self.directory, self.emit = manifest, directory, emit
        directory.mkdir(parents=True, exist_ok=True)

    def call(self, model, payload, files=None, frames=None):
        manifest = {"files": dict((self.manifest or {}).get("files", {}))}
        for name, text in (files or {}).items():
            manifest["files"]["project/" + name] = {"text": text}
        value, report = native_plan(
            self.content,
            self.brief,
            self.settings,
            manifest,
            self.directory / f"call-{len(list(self.directory.glob('call-*'))):03}",
            self.runner,
            self.emit,
            engineering_contract={"schema": schema(model), "payload": payload, "frames": frames or []},
        )
        return model.model_validate(value), report

    def plan(self):
        plan, report = self.call(
            ProductionPlan,
            {
                "phase": "production-planning",
                "visual_constraints": {
                    "max_elements": PATTERN_ELEMENT_LIMITS,
                    "max_label_characters": PATTERN_LABEL_LIMITS,
                    "layout": "grid or fan; fan is available only for overview",
                    "overflow": "Split into multiple scenes or author custom TSX; never silently discard elements or text",
                },
                "instruction": "Create an audience-focused production plan, full fluent narration, art direction and per-scene visual/motion treatment. For key explanatory scenes provide motion with purpose, chapter, stable element IDs and events anchored to actual narration phrases. Choose patterns by explanatory relationship, not keyword matching. Use code_scan, compare, graph, capacity, queue, depth or overview where appropriate; custom TSX remains available. Explain mechanisms visually; do not repeat text cards. Use real UI capture when supplied. All source assertions require supplied evidence IDs.",
            },
        )
        board = validate_design(plan.storyboard.model_dump(), self.content, self.brief)
        return plan, board, report

    def decide(self, workspace, plan):
        instructions = (ROOT / "docs/design/authoring-contract.md").read_text()
        frames = [
            workspace.root / f["name"]
            for f in workspace.state["frames"] + workspace.state.get("motion_frames", [])
        ]
        files = {
            str(p.relative_to(workspace.project)): p.read_text()
            for p in workspace.project.rglob("*")
            if p.is_file()
            and p.suffix in {".ts", ".tsx", ".json", ".md", ".css"}
            and "node_modules" not in p.parts
        }
        action, _ = self.call(
            EngineeringAction,
            {
                "phase": "engineering-loop",
                "contract": instructions,
                "production_plan": plan,
                "current_hash": workspace.fingerprint(),
                "status": {
                    k: workspace.state[k] for k in ["build_hash", "preview_hash", "review_hash", "review"]
                },
                "observations": workspace.state["journal"][-12:],
                "frame_names": [f["name"] for f in workspace.state["frames"]],
                "motion_frame_names": [f["name"] for f in workspace.state.get("motion_frames", [])],
                "motion_review_scope": "Contact sheets sample motion; do not claim full playback or listening",
            },
            files,
            frames,
        )
        return action
