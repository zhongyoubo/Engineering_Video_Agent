"""Native planning and engineering actions. No template or model fallback."""

from ...semantic_scene import semantic_guidance
from ...spatial_scene import spatial_asset_keys
from ...creative_scene import creative_asset_keys, creative_guidance
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
        self.image_catalog = []
        self.catalog_frames = []
        self.settings, self.runner, self.content, self.brief = settings, runner, content, brief
        self.manifest, self.directory, self.emit = manifest, directory, emit
        directory.mkdir(parents=True, exist_ok=True)

    def load_image_catalog(self, db, store, tenant, project_id):
        from ..assets.project_images import catalog, resolve_image
        from ..assets.raster import canonical_png

        self.image_catalog, self.catalog_frames = [], []
        directory = self.directory / "image-catalog"
        directory.mkdir(exist_ok=True)
        for item in catalog(db, tenant, project_id):
            _, preview, _ = canonical_png(resolve_image(db, store, tenant, project_id, item["id"]))
            path = directory / (item["id"] + ".png")
            path.write_bytes(preview)
            self.image_catalog.append({**item, "image_index": len(self.catalog_frames)})
            self.catalog_frames.append(path)

    def material_previews(self, library):
        """A bounded actual-image sheet, not names alone; no source imports/evaluation."""
        from PIL import Image, ImageDraw
        from ...material_packs import resolve_material

        entries = [m for m in library["items"] if m.get("pack_id") and m.get("preview")][:64]
        if not entries:
            return [], []
        sheet = Image.new("RGB", (1200, 220 * ((len(entries) + 3) // 4)), "#edf1f1")
        draw = ImageDraw.Draw(sheet)
        metadata = []
        for i, item in enumerate(entries):
            pack, entry, files, stamp = resolve_material(f"library:{item['id']}@{item['version']}")
            im = Image.open(files[entry.preview]).convert("RGBA")
            im.thumbnail((250, 170))
            x, y = (i % 4) * 300, (i // 4) * 220
            sheet.paste(im, (x + (300 - im.width) // 2, y + 6), im)
            draw.text((x + 6, y + 184), item["id"], fill="#18364b")
            metadata.append(
                dict(id=item["id"], version=item["version"], sheet_index=len(self.catalog_frames), cell=i)
            )
        path = self.directory / "material-catalog.png"
        sheet.save(path)
        return metadata, [path]

    def asset_capabilities(self):
        from ..assets.image_service import configured

        return dict(
            component_svg=True,
            project_image=True,
            image_service=configured(self.settings),
            library_asset=True,
        )

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
        preview_metadata, pack_frames = self.material_previews(library)
        plan, report = self.call(
            ProductionPlan,
            {
                "phase": "production-planning",
                "content_guidance": planning_guidance(self.brief),
                "visual_scene_toolkit": visual_scene_guidance(),
                "semantic_scene_toolkit": semantic_guidance(),
                "creative_production": creative_guidance(),
                "asset_capabilities": self.asset_capabilities(),
                "project_image_catalog": self.image_catalog,
                "material_library": library,
                "material_preview_index": preview_metadata,
                "material_usage": "Inspect actual preview sheet and choose by purpose, style, recognizable subject and affordance. Record exact library:<id>@<version> in shot.assets. Components: creation kit element.library_ref, select_materials, import advertised module/symbol. Images/models: library_asset requirement with library_ref, then asset element.asset_key. GLB requires technique three and LibraryModel. PNG remains 2D. Search filters are discovery, not a topic router. Custom source remains allowed. No network or npm install; only curated offline packs. Preview/license metadata is not consumption or quality acceptance.",
                "visual_constraints": {
                    "scope": "Only the explicitly selected legacy motion/diagram spec; custom creative source is not restricted to these layouts or subject types",
                    "legacy_max_elements": PATTERN_ELEMENT_LIMITS,
                    "legacy_max_label_characters": PATTERN_LABEL_LIMITS,
                    "layout": "Author a suitable free composition. Grid/fan restrictions belong only to legacy motion specs",
                    "overflow": "Split into multiple scenes or author custom TSX; never silently discard elements or text",
                },
                "instruction": EDITORIAL_INSTRUCTION
                + " Create full fluent narration, art direction and per-scene visual/motion treatment. Prefer recognizable objects and causal actions when explaining concrete devices, mechanisms or situations. Use visual_scene for supported objects; custom SVG/TSX remains available for unsupported subjects. Define initial state, action, visible result, real ports and distinct video/audio/control signals, not boxes containing object names. Choose varied treatments by explanatory need. Anchor events to narration phrases. Use supplied real UI captures. All source assertions require supplied evidence IDs.",
            },
            frames=[*self.catalog_frames, *pack_frames],
            validate=lambda candidate: self.prepare_plan(candidate, library, require_creation=True),
        )
        report = {**report, "material_library_revision": library["revision"]}
        board = self.prepare_plan(plan, library, require_creation=True)
        return plan, board, report

    def prepare_plan(self, plan, library, require_creation=False):
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
        declared = {r.id for shot in plan.shots for r in shot.asset_requirements}
        for scene in board.scenes:
            if require_creation and scene.creation is None:
                raise NativeOutputError(
                    "Design a concrete creation plan for every engineering scene; stock components alone are not a creative plan."
                )
            if scene.creation:
                from .workspace import source_path, EngineeringError

                for path in [
                    scene.creation.scene_source,
                    *[e.source_file for e in scene.creation.elements if e.source_file],
                ]:
                    try:
                        source_path(path)
                    except EngineeringError as exc:
                        raise NativeOutputError(
                            "Creative files must be editable authored source paths"
                        ) from exc
                if creative_asset_keys(scene.model_dump()) - declared:
                    raise NativeOutputError(
                        "Declare every creative image in the project-wide asset requirements."
                    )
                allowed = {f"library:{m['id']}@{m['version']}": m for m in library["items"]}
                for element in scene.creation.elements:
                    if element.library_ref and (
                        element.library_ref not in allowed
                        or allowed[element.library_ref].get("asset_type") != "component"
                    ):
                        raise NativeOutputError(
                            "Kit elements require an advertised source component library version"
                        )
            if scene.semantic_scene:
                references = {e.asset_key for e in scene.semantic_scene.entities if e.asset_key}
                references.update(key for e in scene.semantic_scene.entities for key in spatial_asset_keys(e))
                if scene.semantic_scene.background_asset_key:
                    references.add(scene.semantic_scene.background_asset_key)
                if references - declared:
                    raise NativeOutputError(
                        "Declare every registered material in the project-wide asset requirements."
                    )
        allowed_images = {item["id"] for item in self.image_catalog}
        for shot in plan.shots:
            for req in shot.asset_requirements:
                if req.provider == "library_asset":
                    from ...material_packs import resolve_material

                    try:
                        pack, item, files, stamp = resolve_material(req.library_ref)
                    except ValueError as exc:
                        raise NativeOutputError("Choose the exact supplied library material version") from exc
                    if item.asset_type == "component":
                        raise NativeOutputError(
                            "Source components use library selection, not binary asset requests"
                        )
                if req.provider == "image_service" and not self.asset_capabilities()["image_service"]:
                    raise NativeOutputError(
                        "Image service is not configured; choose an available representation or stop with a concrete missing-service diagnostic."
                    )
                if req.provider == "project_image" and req.project_asset_id not in allowed_images:
                    raise NativeOutputError("Choose image IDs from this project's supplied catalog only.")
        by_shot = {s.scene_id: s for s in plan.shots}
        evidence = {e.id for e in self.content.evidence}
        for scene in board.scenes:
            if scene.semantic_scene:
                if by_shot[scene.id].intent is None:
                    raise NativeOutputError("Semantic shots require a structured visual intent")
                if any(set(e.evidence_ids) - evidence for e in scene.semantic_scene.entities):
                    raise NativeOutputError("Semantic observed content references unknown evidence")
        prepare_presentation(board, self.brief, plan.editorial)
        try:
            require_publishable(board, self.content)
        except EditorialError as exc:
            # EditorialError messages are controlled by publication policy, never provider output.
            raise NativeOutputError(str(exc)) from exc
        return board

    def decide(self, workspace, plan):
        import json

        current_props = json.loads((workspace.project / "props.json").read_text())
        library = material_library()
        preview_metadata, pack_frames = self.material_previews(library)
        instructions = (ROOT / "docs/design/authoring-contract.md").read_text()
        frames = [
            *self.catalog_frames,
            *pack_frames,
            *[
                workspace.root / f["name"]
                for f in workspace.state["frames"] + workspace.state.get("motion_frames", [])
            ],
        ]
        frames += [
            workspace.project / "public" / r["preview_filename"]
            for r in workspace.state.get("generated_assets", {}).values()
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
                "material_library": library,
                "material_preview_index": preview_metadata,
                "material_selection": workspace.state.get("material_selection", {}),
                "creative_production": creative_guidance(),
                "current_scene_creation": {
                    s["id"]: s["creation"] for s in current_props.get("scenes", []) if s.get("creation")
                },
                "contract": instructions,
                "production_plan": plan,
                "current_hash": workspace.fingerprint(),
                "semantic_contract": "When using semantic_scene, compose SceneRenderer from ./semantic-kit. Free authored SVG/Canvas/Three scenes instead implement props.scenes[].creation with their own source assets and compiled_creative_events; no kit wrapper is mandatory. It uses software concepts and bound device surfaces; Root owns audio/captions. State changes require measured events and explicit expectations. SpatialCity uses frame-driven 3D camera/instances; QuantityMatrix consumes registered spatial.asset_keys; NodeNetwork preserves node identities/edges and propagates by graph hops using spatial.effect_parameter_id. Use bounded spatial data and shared parameter_id; an immersive spatial shot has one entity, show_heading=false and no physical object stage. Choose by explanatory need, never keyword routing. Declare every spatial.asset_keys key in asset_requirements and review every scene:key binding. Use request_assets for original SVG documents; inspect_asset validates its bytes and metadata. Reference the request ID in AssetImage.asset_key; props.generated_assets is platform-owned. Use only advertised asset_capabilities. Request image_service for recognizable illustrations and transparent cutouts; use project_image only with catalog IDs. No provider substitution. Compose background_asset_key and unframed AssetImage artwork plus measured transform events; retain provenance in reports without unsolicited in-film demo notices. Review every scene_id:expectation_id and score semantic_accuracy >=4 against actual before/during/after frames, not decorative pixels.",
                "asset_capabilities": self.asset_capabilities(),
                "project_image_catalog": self.image_catalog,
                "asset_review_contract": "Review every scene_id:asset_key background/element binding visible in actual frames. Score asset_visibility >=4, name all asset_expectations; generated receipts alone are not consumption. Use globally unique asset IDs; repeated IDs require identical requests.",
                "generated_assets": {
                    k: {
                        f: v
                        for f, v in r.items()
                        if f
                        not in {"svg", "image_png", "request", "preview_png", "file_data", "license_text"}
                    }
                    for k, r in workspace.state.get("generated_assets", {}).items()
                },
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
