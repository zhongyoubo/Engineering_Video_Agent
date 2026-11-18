"""Native planning and engineering actions. No template or model fallback."""

from pydantic import ValidationError
from ...adapters.native_agent import native_plan, NativeOutputError
from ...adapters.native_contract import validate_design
from ...config import ROOT
from ...content_taxonomy import planning_guidance
from ...visual_scene import visual_scene_guidance
from ...specs import PATTERN_ELEMENT_LIMITS, PATTERN_LABEL_LIMITS
from ..materials import material_library, validate_material_references
from ..editorial import EDITORIAL_INSTRUCTION, prepare_presentation, require_publishable, EditorialError
from .contracts import ProductionPlan, EngineeringAction, schema


class NativeEngineeringAgent:
    def __init__(self, settings, runner, content, brief, manifest, directory, emit):
        self.settings, self.runner, self.content, self.brief = settings, runner, content, brief
        self.manifest, self.directory, self.emit = manifest, directory, emit
        directory.mkdir(parents=True, exist_ok=True)

    def call(self, model, payload, files=None, frames=None, validate=None):
        def validate_response(value):
            try:
                parsed = model.model_validate(value)
            except ValidationError as exc:
                # Do not echo Pydantic input/context or untrusted field names to the provider/logs.
                raise NativeOutputError(
                    "Match all required schema fields, enum choices, bounds and cross-field constraints."
                ) from exc
            if validate:
                try:
                    validate(parsed)
                except EditorialError as exc:
                    raise NativeOutputError(str(exc)) from exc
            return parsed

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
            validate_result=validate_response,
        )
        return model.model_validate(value), report

    def plan(self):
        library = material_library()
        plan, report = self.call(
            ProductionPlan,
            {
                "phase": "production-planning",
                "content_guidance": planning_guidance(self.brief),
                "visual_scene_toolkit": visual_scene_guidance(),
                "material_library": library,
                "material_usage": "Choose materials by explanatory purpose; record selected entries as library:<id>@<version> in shot.assets. Custom TSX remains allowed. Unverified assets need actual rendering/review. Reference footage is not reusable material.",
                "visual_constraints": {
                    "max_elements": PATTERN_ELEMENT_LIMITS,
                    "max_label_characters": PATTERN_LABEL_LIMITS,
                    "layout": "grid or fan; fan is available only for overview",
                    "overflow": "Split into multiple scenes or author custom TSX; never silently discard elements or text",
                },
                "instruction": EDITORIAL_INSTRUCTION
                + " Create full fluent narration, art direction and per-scene visual/motion treatment. Prefer recognizable objects and causal actions when explaining concrete devices, mechanisms or situations. Use visual_scene for supported objects; custom SVG/TSX remains available for unsupported subjects. Define initial state, action, visible result, real ports and distinct video/audio/control signals, not boxes containing object names. Choose varied treatments by explanatory need. Anchor events to narration phrases. Use supplied real UI captures. All source assertions require supplied evidence IDs.",
            },
            validate=lambda candidate: self.prepare_plan(candidate, library),
        )
        report = {**report, "material_library_revision": library["revision"]}
        board = self.prepare_plan(plan, library)
        return plan, board, report

    def prepare_plan(self, plan, library):
        try:
            validate_material_references(plan, library)
        except ValueError as exc:
            raise NativeOutputError(
                "Use only supplied, non-blocked material-library IDs and exact versions."
            ) from exc
        try:
            board = validate_design(plan.storyboard.model_dump(), self.content, self.brief)
        except ValueError as exc:
            raise NativeOutputError(
                "Storyboard scenes must satisfy the scene schema and reference only supplied evidence IDs."
            ) from exc
        if self.brief.presentation_profile == "creator" and plan.editorial is None:
            raise EditorialError("创作者制作方案缺少内容主张与观众收益，请补充 editorial 策划。")
        if self.brief.presentation_profile == "creator" and plan.editorial.strategy is None:
            raise EditorialError("新创作者策划必须解析表达目的、讲述对象、观众与表现形式，并给出叙事结构。")
        prepare_presentation(board, self.brief, plan.editorial)
        try:
            require_publishable(board, self.content)
        except EditorialError as exc:
            # EditorialError messages are controlled by publication policy, never provider output.
            raise NativeOutputError(str(exc)) from exc
        return board

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
                "content_guidance": planning_guidance(self.brief),
                "purpose_review": "Score purpose_fulfillment >=4/5 from the actual editorial.strategy outline, success_criteria, script and visuals. A filled structure is not proof of coherent argument, useful advice, understood mechanism or a usable tutorial. Include any unmet purpose-specific criteria in review.issues.",
                "object_scene_review": "For scenes with visual_scene, use ObjectScene from ./scene-objects inside your authored visual code. It renders on a 1920x1080 logical canvas; do not double-scale. Trusted Root supplies ObjectSceneSounds, narration and captions. Score object_fidelity and causal_motion >=4: actual TV/device silhouettes and ports, connected cable, differentiated picture/audio/control movement, visibly changing screen/power/volume states. Inspect continuous samples; do not accept graph boxes labeled TV as object fidelity. Unknown objects require your own appropriate SVG/TSX, not a mislabeled built-in. Decorative waves are illustrations, not hardware measurements.",
                "editorial_review": "When props.presentation_profile is creator, score content_focus, cover_promise, opening_closing and viewer_presentation from actual script/props and rendered images. All must be at least 4, including the separate thumbnail and frame zero. No claim of full playback/listening from sampled frames.",
            },
            files,
            frames,
        )
        return action
