import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.api import app
from explainer.services.engineering.contracts import (
    ProductionPlan,
    EngineeringAction,
    schema,
)
from explainer.adapters.native_contract import strict_schema
from explainer.domain import Brief, ContentIR, Scene, StoryboardIR, Finding
from explainer.specs import (
    RenderProfile,
    VoiceSpec,
    SceneSpec,
    MotionEvent,
    CompiledEvent,
)

from explainer.visual_scene import VisualScene, SceneObject, ObjectPort, SceneConnection, ObjectEvent, CompiledObjectEvent

from explainer.editorial import EditorialBrief, EditorialPlan, CoverSpec, ViewerDisclosure, ContentStrategy, NarrativeBeat
from explainer.content_taxonomy import taxonomy_options

directory = ROOT / "packages/contracts"
for model in [
    Brief,
    VisualScene,
    SceneObject,
    ObjectPort,
    SceneConnection,
    ObjectEvent,
    CompiledObjectEvent,
    EditorialBrief,
    ContentStrategy,
    NarrativeBeat,
    EditorialPlan,
    CoverSpec,
    ViewerDisclosure,
    ContentIR,
    Scene,
    StoryboardIR,
    Finding,
    RenderProfile,
    VoiceSpec,
    SceneSpec,
    MotionEvent,
    CompiledEvent,
]:
    (directory / (model.__name__ + ".schema.json")).write_text(
        json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
    )
(directory / "openapi.json").write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
)
(directory / "AgentDesign.schema.json").write_text(
    json.dumps(strict_schema(), ensure_ascii=False, indent=2) + "\n"
)
for model in [ProductionPlan, EngineeringAction]:
    (directory / (model.__name__ + ".schema.json")).write_text(
        json.dumps(schema(model), ensure_ascii=False, indent=2) + "\n"
    )
(directory / "content-taxonomy.json").write_text(json.dumps(taxonomy_options(), ensure_ascii=False, indent=2) + "\n")
print("Contracts exported")
