import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier
from zipfile import ZipFile

import pytest
from PIL import Image

from explainer import api_materials
from explainer.config import Settings
from explainer.local_materials import catalog
from explainer.semantic_scene import AssetRequirement
from explainer.services.assets.project_images import resolve_image_with_source
from explainer.services.assets.registry import request_assets, restore_assets
from explainer.storage import Storage
from test_semantic_scenes import workspace


def register_png(tmp_path, settings):
    root = tmp_path / "operator-library"
    settings.local_material_dir = root
    source = tmp_path / "source.png"
    Image.new("RGBA", (800, 600), (50, 130, 110, 255)).save(source)
    script = Path(__file__).resolve().parents[3] / "scripts/local_material_library.py"
    subprocess.run(
        [sys.executable, str(script), "--root", str(root), "add", "--id", "agent-notes",
         "--title", "Agent 笔记", "--origin", "作者自制", "--rights", "项目内使用", "--file", str(source)],
        check=True, capture_output=True, text=True,
    )
    return root


def test_external_local_image_is_imported_into_owned_project(client, settings, headers, tmp_path, db):
    root = register_png(tmp_path, settings)
    listing = client.get("/api/v3/local-materials", headers=headers).json()
    assert listing["configured"] is True
    assert [(item["id"], item["origin"]) for item in listing["items"]] == [("agent-notes", "作者自制")]
    preview = client.get("/api/v3/local-materials/agent-notes/preview", headers=headers)
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
    with Image.open(BytesIO(preview.content)) as thumbnail:
        assert thumbnail.size == (320, 240)
    assert preview.headers["cache-control"] == "private, no-cache"
    revalidated = {**headers, "If-None-Match": preview.headers["etag"]}
    assert client.get("/api/v3/local-materials/agent-notes/preview", headers=revalidated).status_code == 304

    project = client.post("/api/v1/projects", headers=headers, json={"name": "Library import"}).json()["id"]
    url = f"/api/v3/projects/{project}/local-materials/agent-notes/import"
    imported = client.post(url, headers=headers)
    assert imported.status_code == 201
    material = imported.json()
    assert material["provenance"] == "local_library"
    assert material["origin"] == "作者自制" and material["rights"] == "项目内使用"
    assert material["source_sha256"] == listing["items"][0]["sha256"]
    assert client.post(url, headers=headers).json()["id"] == material["id"]
    assert client.post(f"{url}?source_sha256={'0' * 64}", headers=headers).status_code == 404
    assert len(client.get(f"/api/v3/projects/{project}/images", headers=headers).json()["items"]) == 1

    other = {"Authorization": "Bearer " + "b" * 32}
    assert client.get("/api/v3/local-materials", headers=other).json()["items"] == []
    assert client.post(url, headers=other).status_code == 404
    assert client.get("/api/v3/local-materials/agent-notes/preview", headers=other).status_code == 404

    work = workspace(tmp_path / "production")
    store = Storage(settings, db)
    request_asset = AssetRequirement(
        id="notes", title="Agent notes", purpose="Show the registered notes image",
        provider="project_image", project_asset_id=material["id"],
    )

    def resolve(image_id):
        return resolve_image_with_source(db, store, "local", project, image_id)

    receipts = request_assets(work, [request_asset], lambda: None, resolve_image=resolve)
    assert request_assets(work, [request_asset], lambda: None) == receipts
    restore_assets(work)
    archive = tmp_path / "export.zip"
    work.export(archive, {})
    with ZipFile(archive) as output:
        receipt = json.loads(output.read("generated-assets.json"))["notes"]
    assert receipt["provider_identity"]["local_material"] == {
        name: material[name] for name in ("local_material_id", "source_sha256", "origin", "rights")
    }

    entry = json.loads((root / "local/index.json").read_text(encoding="utf-8"))["items"][0]
    (root / "local" / entry["file"]).write_bytes(b"changed")
    assert client.post(url, headers=headers).status_code == 404
    assert client.get("/api/v3/local-materials/agent-notes/preview", headers=headers).status_code == 404
    assert client.get("/api/v3/local-materials/agent-notes/preview", headers=revalidated).status_code == 404
    assert len(client.get(f"/api/v3/projects/{project}/images", headers=headers).json()["items"]) == 1


def test_local_library_rejects_symlinked_and_forged_files(tmp_path):
    root = tmp_path / "library"
    folder = root / "local"
    folder.mkdir(parents=True)
    (folder / "index.json").write_text(json.dumps({
        "schema_version": 1,
        "items": [{"id": "bad", "title": "Bad", "origin": "test", "rights": "test",
                   "sha256": "a" * 64, "file": "../secret.png"}],
    }), encoding="utf-8")
    try:
        catalog(root, "local")
    except ValueError:
        pass
    else:
        raise AssertionError("Forged path was accepted")


def test_local_library_returns_conflict_for_malformed_index(client, settings, headers, tmp_path):
    root = register_png(tmp_path, settings)
    index = root / "local/index.json"
    malformed = json.loads(index.read_text(encoding="utf-8"))
    malformed["items"][0]["id"] = []
    index.write_text(json.dumps(malformed), encoding="utf-8")
    assert client.get("/api/v3/local-materials", headers=headers).status_code == 409


def test_local_library_rejects_case_colliding_tenants(tmp_path):
    with pytest.raises(ValueError, match="distinct names"):
        Settings(
            data_dir=tmp_path, api_token="a" * 32, local_material_dir=tmp_path / "library",
            tenant_keys=json.dumps({"Team": "b" * 32, "team": "c" * 32}),
        ).prepare()


def test_concurrent_imports_reuse_the_same_project_image(client, settings, headers, tmp_path, monkeypatch):
    register_png(tmp_path, settings)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Concurrent import"}).json()["id"]
    url = f"/api/v3/projects/{project}/local-materials/agent-notes/import"
    read_image = api_materials.image_bytes
    barrier = Barrier(2)

    def synchronized_read(*args):
        result = read_image(*args)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(api_materials, "image_bytes", synchronized_read)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(url, headers=headers), range(2)))
    assert all(response.status_code == 201 for response in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(client.get(f"/api/v3/projects/{project}/images", headers=headers).json()["items"]) == 1
