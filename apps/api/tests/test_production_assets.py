"""Real raster parsing/ingestion/recovery; gateway transport responses are deliberately mocked."""

import base64
import hashlib
import io
import json
import pytest
import httpx
from PIL import Image, PngImagePlugin
from explainer.config import Settings
from explainer.semantic_scene import AssetRequirement
from explainer.services.assets import image_service
from explainer.services.assets.raster import canonical_png
from explainer.services.assets.project_images import resolve_image
from explainer.services.assets.registry import request_assets, restore_assets
from explainer.services.engineering.controller import EngineeringController
from explainer.services.engineering.contracts import EngineeringAction
from explainer.services.engineering.workspace import EngineeringError
from explainer.services.motion import compile_motion
from explainer.storage import Storage
from test_semantic_scenes import workspace, spec, scene, words


def png(transparent=False):
    image = Image.new("RGBA", (128, 96), (235, 75, 55, 255))
    if transparent:
        image.putpixel((0, 0), (0, 0, 0, 0))
    out = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("untrusted", "provider internal prompt")
    image.save(out, format="PNG", pnginfo=metadata)
    return out.getvalue()


def req(provider="image_service", **extra):
    return AssetRequirement(
        id="tomato",
        purpose="清楚呈现晚餐所需的番茄",
        title="番茄",
        provider=provider,
        **(
            {"image_prompt": "A recognizable clay tomato cutout, red and green, isolated object"}
            if provider == "image_service"
            else {}
        ),
        **extra,
    )


def configured_settings(**extra):
    return Settings(
        image_service_url="https://gateway.example/render",
        image_service_key="secret-image-key",
        image_service_model="fixture-model",
        **extra,
    )


def gateway(monkeypatch, handler):
    client = httpx.Client
    monkeypatch.setattr(
        image_service.httpx,
        "Client",
        lambda **kw: client(**{**kw, "transport": httpx.MockTransport(handler)}),
    )


def test_gateway_request_is_mediated_bounded_and_private(tmp_path, monkeypatch):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"png_base64": base64.b64encode(png(True)).decode(), "request_id": "img-123"}
        )

    gateway(monkeypatch, respond)
    w = workspace(tmp_path)
    settings = configured_settings()
    first = request_assets(w, [req(transparent=True)], lambda: None, settings, scope="tenant:revision")
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["protocol"] == "eva-image-1" and payload["transparent"]
    assert requests[0].headers["authorization"] == "Bearer secret-image-key"
    assert first[0]["format"] == "png" and first[0]["has_alpha"]
    assert not {"image_png", "preview_png", "svg", "request"} & first[0].keys()
    assert "secret-image-key" not in json.dumps(w.state)
    assert (
        request_assets(w, [req(transparent=True)], lambda: None, settings, scope="tenant:revision") == first
    )
    assert len(requests) == 1
    stamp = w.fingerprint()
    path = w.project / "public" / first[0]["filename"]
    path.unlink()
    restore_assets(w)
    assert len(requests) == 1 and w.fingerprint() == stamp
    assert "untrusted" not in Image.open(path).info
    # A provider revision changes the request key and triggers a fresh request.
    settings.image_service_revision = "2"
    request_assets(w, [req(transparent=True)], lambda: None, settings, scope="tenant:revision")
    assert len(requests) == 2
    assert requests[0].headers["idempotency-key"] != requests[1].headers["idempotency-key"]


@pytest.mark.parametrize("case", ["redirect", "url", "invalid_png", "opaque_cutout", "error", "bad_base64"])
def test_gateway_failures_never_publish_or_substitute(tmp_path, monkeypatch, case):
    def respond(_):
        if case == "redirect":
            return httpx.Response(302, headers={"Location": "http://169.254.169.254"})
        if case == "url":
            return httpx.Response(200, json={"url": "http://169.254.169.254"})
        if case == "error":
            raise httpx.ConnectError("credential=secret-image-key")
        data = b"not png" if case == "invalid_png" else png()
        return httpx.Response(
            200, json={"png_base64": "!!!" if case == "bad_base64" else base64.b64encode(data).decode()}
        )

    gateway(monkeypatch, respond)
    w = workspace(tmp_path)
    with pytest.raises(ValueError) as exc:
        request_assets(w, [req(transparent=case == "opaque_cutout")], lambda: None, configured_settings())
    assert "secret-image-key" not in str(exc.value)
    assert not w.state["generated_assets"] and not list((w.project / "public").rglob("*.png"))


def test_cancel_after_paid_response_cannot_publish(tmp_path, monkeypatch):
    canceled = False

    def respond(_):
        nonlocal canceled
        canceled = True
        return httpx.Response(200, json={"png_base64": base64.b64encode(png()).decode()})

    def guard():
        if canceled:
            raise RuntimeError("lost lease")

    gateway(monkeypatch, respond)
    w = workspace(tmp_path)
    with pytest.raises(RuntimeError, match="lost lease"):
        request_assets(w, [req()], guard, configured_settings())
    assert not w.state["generated_assets"]


@pytest.mark.parametrize("case", ["image_png", "preview_png", "filename", "sha256"])
def test_raster_receipt_recovery_rejects_tampering(tmp_path, case):
    w = workspace(tmp_path)
    r = req("project_image", project_asset_id="mat_" + "a" * 32)
    request_assets(w, [r], lambda: None, resolve_image=lambda _: png())
    old = w.state["generated_assets"]["tomato"]
    path = w.project / "public" / old["filename"]
    path.unlink()
    old[case] = "../../unsafe" if case == "filename" else "corrupt"
    with pytest.raises(ValueError):
        restore_assets(w)
    assert not path.exists()


def test_project_upload_ownership_and_controller_integration(client, headers, settings, db, tmp_path):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "晚餐"}).json()["id"]
    other_project = client.post("/api/v1/projects", headers=headers, json={"name": "另一项目"}).json()["id"]
    url = f"/api/v3/projects/{project}/images"
    response = client.post(
        url, headers=headers, data={"title": "番茄"}, files={"file": ("tomato.png", png(), "image/png")}
    )
    assert response.status_code == 201, response.text
    material = response.json()
    assert material["provenance"] == "user_import"
    assert client.get(url, headers=headers).json()["items"] == [material]
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer " + "b" * 32}).status_code == 404
    assert client.get(f"/api/v3/projects/{other_project}/images", headers=headers).json()["items"] == []
    store = Storage(settings, db)
    # Local default tenant is named default, not inferred from an arbitrary material ID.
    tenant = db.one("SELECT tenant FROM projects WHERE id=?", (project,))["tenant"]
    with pytest.raises(ValueError):
        resolve_image(db, store, tenant, other_project, material["id"])
    with pytest.raises(ValueError):
        resolve_image(db, store, "other", project, material["id"])
    w = workspace(tmp_path)
    controller = EngineeringController(
        w,
        None,
        None,
        lambda _: None,
        lambda *a: None,
        lambda: None,
        resolve_image=lambda id: resolve_image(db, store, tenant, project, id),
    )
    controller.apply(
        EngineeringAction(
            action="request_assets",
            summary="注册项目插画",
            files=[],
            review=None,
            asset_requests=[req("project_image", project_asset_id=material["id"])],
        )
    )
    controller.apply(
        EngineeringAction(
            action="inspect_asset", summary="校验实际图片", files=[], review=None, asset_id="tomato"
        )
    )
    assert w.state["journal"][-1]["kind"] == "asset.inspected"
    assert "image_png" not in json.dumps(w.state["journal"])
    registered = w.state["generated_assets"]["tomato"]
    path = w.project / "public" / registered["filename"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == material["sha256"]
    stamp = w.fingerprint()
    w.state.update(build_hash=stamp, preview_hash=stamp, review_hash=stamp, finished=True)
    request_assets(w, [req("project_image", project_asset_id=material["id"])], lambda: None)
    assert w.state["finished"] and w.fingerprint() == stamp
    path.write_bytes(b"corrupt")
    with pytest.raises(EngineeringError):
        controller.apply(
            EngineeringAction(
                action="inspect_asset", summary="再次校验", files=[], review=None, asset_id="tomato"
            )
        )


def test_invalid_upload_and_capability_truth(client, headers, settings):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Test"}).json()["id"]
    response = client.post(
        f"/api/v3/projects/{project}/images",
        headers=headers,
        data={"title": "图片"},
        files={"file": ("x.png", b"bad", "image/png")},
    )
    assert response.status_code == 422
    assert not client.get("/api/v1/capabilities", headers=headers).json()["asset_factory"]["image_service"]
    settings.image_service_url = "https://gateway.example/render"
    settings.image_service_key = "private-image-key"
    settings.image_service_model = "fixture"
    result = client.get("/api/v1/capabilities", headers=headers)
    assert result.json()["asset_factory"]["image_service"]
    assert settings.image_service_key not in result.text and settings.image_service_url not in result.text


def test_measured_transform_has_causal_result_and_rejects_bad_geometry():
    d = spec()
    d["entities"][0].update(
        component="AssetImage", asset_key="tomato", image_style="artwork", width=200, height=180, opacity=0
    )
    d["events"] = [
        dict(
            id="fly",
            target=d["entities"][0]["id"],
            action="transform",
            anchor={"phrase": "开始查询"},
            duration_ms=500,
            x=700,
            y=220,
            opacity=1,
            scale=1.2,
        )
    ]
    d["expectations"] = [dict(id="arrived", event_id="fly", visible_result="番茄从左侧飞到食材盘上")]
    s = scene(d)
    compile_motion(s, words(), 30)
    assert s.compiled_semantic_events[0].timing_source == "measured_words"
    assert s.compiled_semantic_events[0].x == 700
    d["events"][0]["x"] = 1520
    d["entities"][0]["width"] = 300
    with pytest.raises(ValueError):
        compile_motion(scene(d), words(), 30)
    d["events"][0]["opacity"] = 2
    with pytest.raises(ValueError):
        scene(d)


def test_import_normalization_and_duplicate_batch_are_bounded(tmp_path):
    blob, preview, meta = canonical_png(png(True), transparent=True)
    assert meta["has_alpha"] and preview.startswith(b"\x89PNG")
    assert "untrusted" not in Image.open(io.BytesIO(blob)).info
    w = workspace(tmp_path)
    r = req("project_image", project_asset_id="mat_" + "a" * 32)
    with pytest.raises(ValueError, match="Duplicate"):
        request_assets(w, [r, r], lambda: None, resolve_image=lambda _: blob)
    assert not w.state["generated_assets"]


def test_legacy_svg_receipts_survive_new_raster_fields(tmp_path):
    from test_semantic_scenes import requirement
    from explainer.services.assets.factory import requirement_key, FACTORY_VERSION
    from explainer.config import ROOT

    r = requirement()
    legacy = {k: r.model_dump()[k] for k in ["id", "purpose", "provider", "title", "items"]}
    old_key = hashlib.sha256(
        json.dumps(
            [
                FACTORY_VERSION,
                hashlib.sha256((ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf").read_bytes()).hexdigest(),
                legacy,
            ],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    assert requirement_key(r) == old_key
    w = workspace(tmp_path)
    request_assets(w, [r], lambda: None)
    stamp = w.fingerprint()
    w.state["generated_assets"][r.id]["request"] = legacy
    restore_assets(w)
    assert w.fingerprint() == stamp


def test_planner_gets_actual_project_preview_without_private_credentials(
    client, headers, settings, db, tmp_path
):
    from explainer.services.engineering.agent import NativeEngineeringAgent

    project = client.post("/api/v1/projects", headers=headers, json={"name": "Images"}).json()["id"]
    uploaded = client.post(
        f"/api/v3/projects/{project}/images",
        headers=headers,
        data={"title": "番茄"},
        files={"file": ("image.png", png(), "image/png")},
    ).json()
    tenant = db.one("SELECT tenant FROM projects WHERE id=?", (project,))["tenant"]
    agent = NativeEngineeringAgent(settings, None, None, None, None, tmp_path / "native", lambda *a: None)
    agent.load_image_catalog(db, Storage(settings, db), tenant, project)
    assert agent.image_catalog[0]["id"] == uploaded["id"] and agent.image_catalog[0]["image_index"] == 0
    assert Image.open(agent.catalog_frames[0]).size == (128, 96)
    assert "image_png" not in json.dumps(agent.image_catalog)
    agent.load_image_catalog(db, Storage(settings, db), "other", project)
    assert not agent.image_catalog and not agent.catalog_frames


def test_gateway_stream_budget_rejects_before_json_decode(tmp_path, monkeypatch):
    monkeypatch.setattr(image_service, "MAX_IMAGE_BYTES", 256)
    gateway(
        monkeypatch,
        lambda _: httpx.Response(200, headers={"Content-Type": "application/json"}, content=b" " * 5000),
    )
    w = workspace(tmp_path)
    with pytest.raises(ValueError, match="oversized"):
        request_assets(w, [req()], lambda: None, configured_settings())
    assert not w.state["generated_assets"]


def test_animation_png_and_oversize_geometry_are_rejected():
    image = Image.new("RGB", (64, 64), "red")
    second = Image.new("RGB", (64, 64), "green")
    out = io.BytesIO()
    image.save(out, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    with pytest.raises(ValueError, match="single-frame"):
        canonical_png(out.getvalue())
    out = io.BytesIO()
    Image.new("RGB", (4097, 64), "blue").save(out, format="PNG")
    with pytest.raises(ValueError, match="geometry"):
        canonical_png(out.getvalue())
