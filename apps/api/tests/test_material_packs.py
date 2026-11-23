"""Real pack bytes/receipts, contract and recovery checks; no generated-code execution."""

import copy
import hashlib
import json
import shutil
import struct
import zipfile

import pytest
from explainer.config import ROOT
from explainer.domain import Scene
from explainer.material_packs import load_packs, resolve_material, relative_file
from explainer.semantic_scene import AssetRequirement
from explainer.services.assets.glb import validate_glb
from explainer.services.assets.registry import request_assets, restore_assets, public_receipt
from explainer.services.engineering.contracts import EngineeringAction
from explainer.services.engineering.workspace import Workspace, EngineeringError, source_path
from explainer.services.material_staging import stage_materials, verify_staged_materials, plan_material_refs
from explainer.services.materials import search_materials


def work(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "noto.otf").write_bytes(b"protocol-only-font")
    w = Workspace(tmp_path / "work")
    s = Scene(id="pack", type="cards", title="素材测试", narration="测试离线素材")
    w.prepare(dict(scenes=[s.model_dump()], total_frames=s.frames), media)
    return w, media


def req(key="notebook", ref="pack.soft3d.notebook"):
    return dict(
        id=key,
        title="具体对象",
        purpose="通过明确的素材对象帮助观众理解",
        provider="library_asset",
        library_ref=f"library:{ref}@1.0",
    )


def test_all_curated_entries_have_pinned_sources_and_real_binary_kinds():
    packs = load_packs()
    assert len(packs) == 4 and sum(len(p.items) for p, *_ in packs) == 14
    for p, directory, files, stamp in packs:
        assert len(p.revision) == 40 and len(stamp) == 64
        assert files[p.license_file].stat().st_size > 100
        assert all(hashlib.sha256(files[f.path].read_bytes()).hexdigest() == f.sha256 for f in p.files)
    assert len(search_materials(style="duotone")["items"]) == 8
    assert [m["id"] for m in search_materials(query="牛油果", asset_type="model")["items"]] == [
        "pack.avocado.model"
    ]
    assert search_materials(query="不存在的素材")["items"] == []
    assert resolve_material("library:pack.soft3d.heart@1.0")[1].parameters["native_size"] == "132×120"
    with pytest.raises(ValueError):
        resolve_material("library:pack.avocado.model@99")


@pytest.mark.parametrize(
    "path", ["../foo", "a//b", "/tmp/x", "a/./b", "a\\b", "node_modules/x", "a/.hidden", "C:x"]
)
def test_pack_paths_never_normalize_or_escape(path):
    with pytest.raises(ValueError):
        relative_file(path)


def test_pack_digest_and_symlink_rejected(monkeypatch, tmp_path):
    import explainer.material_packs as packs

    dest = tmp_path / "packs"
    dest.mkdir()
    shutil.copytree(ROOT / "assets/library/packs/phosphor", dest / "phosphor")
    (dest / "index.json").write_text('["phosphor/manifest.json"]')
    monkeypatch.setattr(packs, "PACK_ROOT", dest)
    source = dest / "phosphor/Icons.tsx"
    original = source.read_bytes()
    source.write_bytes(original + b"//changed")
    with pytest.raises(ValueError, match="hash"):
        load_packs()
    source.unlink()
    outside = tmp_path / "external.tsx"
    outside.write_bytes(original)
    source.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        load_packs()


def test_selective_staging_protection_invalidation_and_clear(tmp_path):
    w, _ = work(tmp_path)
    ref = "library:pack.phosphor.book-open@1.0"
    selected = stage_materials(w, [ref])
    assert verify_staged_materials(w) == selected
    assert (w.project / "src/vendor/phosphor/Icons.tsx").is_file()
    assert not (w.project / "src/vendor/motion").exists()
    assert not w.state["build_hash"]
    stamp = w.fingerprint()
    w.state["build_hash"] = stamp
    stage_materials(w, [ref])
    assert w.fingerprint() == stamp and w.state["build_hash"] == stamp
    for name in ["src/vendor/phosphor/Icons.tsx", "src/sub/library-model.tsx"]:
        with pytest.raises(EngineeringError):
            source_path(name)
    stage_materials(w, [])
    assert not list((w.project / "src/vendor").rglob("*.tsx"))
    assert w.state["build_hash"] is None


def test_tampered_and_forged_staged_manifest_is_rejected(tmp_path):
    w, _ = work(tmp_path)
    stage_materials(w, ["library:pack.motion.typewriter@1.0"])
    p = w.project / "src/vendor/motion/MotionText.tsx"
    p.write_text("changed")
    with pytest.raises(ValueError, match="bytes"):
        verify_staged_materials(w)
    w.state["material_selection"]["files"]["src/vendor/motion/MotionText.tsx"] = hashlib.sha256(
        p.read_bytes()
    ).hexdigest()
    with pytest.raises(ValueError, match="manifest"):
        verify_staged_materials(w)
    stage_materials(w, [])
    (w.project / "src/vendor/unreviewed.tsx").write_text("extra")
    with pytest.raises(ValueError, match="Undeclared"):
        verify_staged_materials(w)


def test_selection_guard_fails_before_publishing(tmp_path):
    w, _ = work(tmp_path)
    stamp = w.fingerprint()

    def cancelled():
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError):
        stage_materials(w, ["library:pack.motion.typewriter@1.0"], cancelled)
    assert w.fingerprint() == stamp and "material_selection" not in w.state


def test_binary_receipts_are_canonical_recoverable_private_and_licensed(tmp_path):
    w, media = work(tmp_path)
    requests = [req(), req("avocado", "pack.avocado.model")]
    result = request_assets(w, requests, lambda: None)
    assert len(result) == 2
    assert result[1]["format"] == "glb" and result[1]["meshes"] == 1
    assert all("file_data" not in r and "license_text" not in r for r in result)
    before = w.fingerprint()
    w.state["build_hash"] = before
    request_assets(w, requests, lambda: None)
    assert w.fingerprint() == before and w.state["build_hash"] == before
    original = copy.deepcopy(w.state["generated_assets"])
    w.record("fixture", {})
    restored = Workspace(w.root)
    restored.prepare(json.loads((w.project / "props.json").read_text()), media)
    assert restored.state["generated_assets"] == original
    assert len(restore_assets(restored)) == 2
    for receipt in original.values():
        assert "file_data" not in public_receipt(receipt)
        assert (w.project / "public" / receipt["filename"]).is_file()
    destination = tmp_path / "project.zip"
    w.export(destination, {})
    with zipfile.ZipFile(destination) as z:
        assert "licenses/avocado.txt" in z.namelist()
        assert "CC0" in z.read("licenses/avocado.txt").decode()
        assert "material-manifest.json" in z.namelist()
        assert "file_data" not in z.read("generated-assets.json").decode()
    w.state["generated_assets"]["avocado"]["filename"] = "../bad.glb"
    with pytest.raises(ValueError, match="inconsistent"):
        restore_assets(w)


def test_invalid_binary_requests_and_embedded_glb_bounds(tmp_path):
    w, _ = work(tmp_path)
    with pytest.raises(ValueError, match="select_materials"):
        request_assets(w, [req("icon", "pack.phosphor.brain")], lambda: None)
    with pytest.raises(ValueError, match="cutout"):
        request_assets(w, [{**req("model", "pack.avocado.model"), "transparent": True}], lambda: None)
    with pytest.raises(ValueError):
        AssetRequirement.model_validate({**req(), "provider": "project_image"})
    raw = (ROOT / "assets/library/packs/avocado/models/Avocado.glb").read_bytes()
    assert validate_glb(raw)["binary_bytes"] == 448224
    for bad in [b"x", raw[:-1], b"BAD!" + raw[4:]]:
        with pytest.raises(ValueError):
            validate_glb(bad)
    size = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20 : 20 + size])
    doc["buffers"][0]["uri"] = "https://example.test/model.bin"
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    tail = raw[20 + size :]
    changed = (
        struct.pack("<4sII", b"glTF", 2, 20 + len(js) + len(tail))
        + struct.pack("<II", len(js), 0x4E4F534A)
        + js
        + tail
    )
    with pytest.raises(ValueError, match="embed"):
        validate_glb(changed)


def test_api_discovery_filters_and_authenticated_previews(client, headers):
    response = client.get("/api/v1/material-library?style=soft3d&asset_type=image", headers=headers)
    assert response.status_code == 200 and len(response.json()["items"]) == 3
    item = response.json()["items"][0]
    assert client.get(item["preview"]).status_code == 401
    preview = client.get(item["preview"], headers=headers)
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG")
    assert (
        client.get(
            "/api/v1/material-library/pack.soft3d.notebook/preview?version=wrong", headers=headers
        ).status_code
        == 404
    )
    assert client.get("/api/v1/material-library?asset_type=unknown", headers=headers).status_code == 422


def test_tool_contract_and_plan_refs_include_both_kinds():
    action = EngineeringAction(
        action="select_materials",
        summary="使用明确版本的书本组件",
        files=[],
        review=None,
        material_refs=["library:pack.phosphor.book-open@1.0"],
    )
    assert action.material_refs == ["library:pack.phosphor.book-open@1.0"]
    assert plan_material_refs(
        dict(shots=[dict(assets=action.material_refs, asset_requirements=[req()])]), dict(scenes=[])
    ) == ["library:pack.phosphor.book-open@1.0", "library:pack.soft3d.notebook@1.0"]
    with pytest.raises(ValueError):
        EngineeringAction(
            action="build",
            summary="错误的混合操作",
            files=[],
            review=None,
            material_refs=action.material_refs,
        )


def test_recursive_dependencies_use_paths_not_only_basenames(monkeypatch, tmp_path):
    import explainer.services.render_plan as render

    monkeypatch.setattr(render, "ROOT", tmp_path)
    template = tmp_path / "packages/engineering-template/src/a"
    template.mkdir(parents=True)
    (template / "same.ts").write_text("one")
    public = tmp_path / "project/public"
    public.mkdir(parents=True)
    props = dict(scenes=[dict(id="one", start_frame=0, frames=30)])
    first = render.build_render_plan(props, public)
    other = template.parent / "b"
    other.mkdir()
    (other / "same.ts").write_text("one")
    second = render.build_render_plan(props, public)
    assert first["renderer_sha256"] != second["renderer_sha256"]
    vendor = public.parent / "src/vendor/nested"
    vendor.mkdir(parents=True)
    (vendor / "a.tsx").write_text("v1")
    third = render.build_render_plan(props, public)
    assert second["scenes"][0]["dependency_key"] != third["scenes"][0]["dependency_key"]
