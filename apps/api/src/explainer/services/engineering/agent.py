"""Native planning and engineering actions. No template or model fallback."""

from ...adapters.native_agent import native_plan
from ...adapters.native_contract import validate_design
from ...config import ROOT
from ...specs import PATTERN_ELEMENT_LIMITS, PATTERN_LABEL_LIMITS
from ..materials import material_library, validate_material_references
from ..editorial import EDITORIAL_INSTRUCTION, prepare_presentation, require_publishable, EditorialError
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
        library = material_library()
        plan, report = self.call(
            ProductionPlan,
            {
                "phase": "production-planning",
                "material_library": library,
                "material_usage": "Choose materials by explanatory purpose; record selected entries as library:<id>@<version> in shot.assets. Custom TSX remains allowed. Unverified assets need actual rendering/review. Reference footage is not reusable material.",
                "visual_constraints": {
                    "max_elements": PATTERN_ELEMENT_LIMITS,
                    "max_label_characters": PATTERN_LABEL_LIMITS,
                    "layout": "grid or fan; fan is available only for overview",
                    "overflow": "Split into multiple scenes or author custom TSX; never silently discard elements or text",
                },
                "instruction": EDITORIAL_INSTRUCTION
                + " Create full fluent narration, art direction and per-scene visual/motion treatment. Anchor events to narration phrases. Choose patterns by explanatory relationship, not keyword matching. Custom TSX remains available. Use supplied real UI captures. All source assertions require supplied evidence IDs.",
            },
        )
        validate_material_references(plan, library)
        report = {**report, "material_library_revision": library["revision"]}
        board = validate_design(plan.storyboard.model_dump(), self.content, self.brief)
        if self.brief.presentation_profile == "creator" and plan.editorial is None:
            raise EditorialError("创作者制作方案缺少内容主张与观众收益，请补充 editorial 策划。")
        prepare_presentation(board, self.brief, plan.editorial)
        require_publishable(board, self.content)
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
                "publication_contract": EDITORIAL_INSTRUCTION,
                "editorial_review": "When props.presentation_profile is creator, score content_focus, cover_promise, opening_closing and viewer_presentation from actual script/props and rendered images. All must be at least 4, including the separate thumbnail and frame zero. No claim of full playback/listening from sampled frames.",
            },
            files,
            frames,
        )
        return action
