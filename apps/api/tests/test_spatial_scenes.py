"""Spatial contracts retain causal timing, asset ownership and protected source boundaries."""

import copy
import pytest
from explainer.domain import Scene, Brief
from explainer.semantic_scene import SemanticScene
from explainer.services.engineering.workspace import source_path, EngineeringError
from explainer.services.assets.usage import asset_usage
from explainer.services.motion import compile_motion


def art(component="NodeNetwork"):
    return dict(
        viewer_question="对象变化时关系是否保持？",
        show_heading=False,
        parameters=[
            dict(id="layout", minimum=0, maximum=1, initial=0),
            dict(id="effect", minimum=0, maximum=1, initial=0),
        ],
        entities=[
            dict(
                id="network",
                component=component,
                title="保持联系",
                width=1920,
                height=1080,
                immersive=True,
                parameter_id="layout",
                spatial=dict(count=48, effect_parameter_id="effect")
                if component == "NodeNetwork"
                else dict(),
            )
        ],
        events=[
            dict(
                id="spread",
                target="layout",
                action="parameter",
                value=1,
                duration_ms=1500,
                anchor=dict(phrase="分散"),
            )
        ],
        expectations=[dict(id="moved", event_id="spread", visible_result="相同节点移动后依然保留连接")],
    )


def test_spatial_states_compile_from_real_word_anchors_and_hold_result():
    scene = Scene(
        id="spatial",
        type="cards",
        title="节点变化",
        narration="分散后保持联系",
        frames=120,
        semantic_scene=art(),
    )
    compile_motion(
        scene, [dict(text="分散", start=0.5, end=1.0), dict(text="后保持联系", start=1.0, end=2.0)], 30
    )
    event = scene.compiled_semantic_events[0]
    assert (event.start_frame, event.end_frame, event.timing_source) == (15, 60, "measured_words")
    assert event.end_frame < scene.frames


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda d: d["entities"][0]["spatial"].update(count=65), "at most 64"),
        (lambda d: d["entities"][0]["spatial"].update(source_node=49), "valid source"),
        (lambda d: d["entities"][0]["spatial"].update(effect_parameter_id="missing"), "missing parameter"),
        (lambda d: d["entities"][0].update(bind_to="tv"), "cannot bind"),
        (lambda d: d.update(show_heading=True), "show_heading=false"),
        (lambda d: d["entities"][0].update(immersive=False), "outside its stage"),
        (lambda d: d["entities"][0].update(spatial=None), "bounded spatial"),
    ],
)
def test_invalid_spatial_state_is_rejected_before_render(change, match):
    d = art()
    change(d)
    with pytest.raises(ValueError, match=match):
        SemanticScene.model_validate(d)


def test_matrix_uses_registered_ids_and_all_bindings_are_reviewed():
    d = art("QuantityMatrix")
    d["entities"][0]["spatial"] = {"asset_keys": ["photo-a", "photo-b"], "count": 240}
    model = SemanticScene.model_validate(d)
    uses = asset_usage({"scenes": [{"id": "matrix", "frames": 120, "semantic_scene": model.model_dump()}]})
    assert set(uses) == {"matrix:photo-a", "matrix:photo-b"}
    bad = copy.deepcopy(d)
    bad["entities"][0]["spatial"]["asset_keys"] = ["https://outside/image.png"]
    with pytest.raises(ValueError, match="registered keys"):
        SemanticScene.model_validate(bad)
    bad = copy.deepcopy(d)
    bad["entities"][0]["spatial"]["asset_keys"] = []
    with pytest.raises(ValueError, match="registered image"):
        SemanticScene.model_validate(bad)
    bad = copy.deepcopy(d)
    bad["entities"][0]["opacity"] = 0
    with pytest.raises(ValueError, match="never visible"):
        asset_usage({"scenes": [{"id": "matrix", "frames": 120, "semantic_scene": bad}]})


def test_new_modules_cannot_be_replaced_by_native_authoring():
    for name in ["spatial-kit.tsx", "spatial-state.ts"]:
        with pytest.raises(EngineeringError):
            source_path("src/" + name)
        with pytest.raises(EngineeringError):
            source_path("src/components/" + name)
    assert (
        Brief(title="空间", prompt="用镜头解释关系", design_pack="neon_horizon").design_pack == "neon_horizon"
    )


def test_immersive_spatial_scene_cannot_cover_a_physical_object_stage():
    with pytest.raises(ValueError, match="separate shot"):
        Scene(
            id="mixed",
            type="cards",
            title="混合",
            narration="分散后保持联系",
            frames=120,
            semantic_scene=art(),
            visual_scene={
                "purpose": "可识别的电视设备",
                "objects": [
                    {
                        "id": "tv",
                        "kind": "tv",
                        "label": "电视",
                        "x": 100,
                        "y": 100,
                        "width": 600,
                        "height": 400,
                    }
                ],
            },
        )


def test_native_plan_requires_every_matrix_asset_declared(settings, tmp_path):
    from test_materials_ming import production_plan
    from explainer.adapters.native_agent import NativeOutputError
    from explainer.services.engineering.agent import NativeEngineeringAgent
    from explainer.services.ingestion import analyze
    from explainer.services.materials import material_library
    from explainer.services.process import Runner

    brief = Brief(title="Test", prompt="Explain a request lifecycle")
    agent = NativeEngineeringAgent(settings, Runner(), analyze(brief), brief, {}, tmp_path, lambda _: None)
    plan = production_plan()
    scene = next(s for s in plan.storyboard.scenes if s.id == "explain")
    data = art("QuantityMatrix")
    data["entities"][0]["spatial"] = {"asset_keys": ["photo-a", "photo-b"], "count": 240}
    scene.narration = "分散后保持联系"
    scene.diagram = None
    scene.motion = None
    scene.semantic_scene = SemanticScene.model_validate(data)
    with pytest.raises(NativeOutputError, match="Declare every registered material"):
        agent.prepare_plan(plan, material_library())
