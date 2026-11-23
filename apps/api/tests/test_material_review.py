"""Regression cases found during pack recovery/lifecycle review; protocol tools never render."""

import copy
import json
import struct
import shutil
from unittest.mock import Mock

import pytest
from explainer.config import ROOT
from explainer.services.engineering.controller import EngineeringController
from explainer.services.material_staging import stage_materials, selection_files
from explainer.services.assets.glb import validate_glb
from test_material_packs import work, req


def test_resume_retains_runtime_material_choices_and_current_acceptance(tmp_path):
    w, _ = work(tmp_path)
    ref = "library:pack.motion.typewriter@1.0"
    stage_materials(w, [ref])
    stamp = w.fingerprint()
    w.state.update(finished=True, build_hash=stamp, preview_hash=stamp, review_hash=stamp)
    tools = Mock()
    tools.execute.return_value = {"ok": True}
    agent = Mock()
    agent.decide.side_effect = AssertionError("Accepted exact source should resume directly")
    c = EngineeringController(w, agent, tools, lambda _: None, lambda *a: None, lambda: None)
    assert c.run({"shots": []}) == {"ok": True}
    assert w.state["material_selection"]["references"] == [ref]
    tools.execute.assert_called_once_with(w, "final")


def test_recovery_rejects_forged_pack_record_before_overwriting(tmp_path):
    w, media = work(tmp_path)
    stage_materials(w, ["library:pack.motion.typewriter@1.0"])
    props = json.loads((w.project / "props.json").read_text())
    w.state["material_selection"]["materials"]["library:pack.motion.typewriter@1.0"]["bundle_sha256"] = (
        "0" * 64
    )
    state = copy.deepcopy(w.state)
    stamp = w.fingerprint()
    with pytest.raises(ValueError, match="manifest"):
        w.prepare(props, media)
    assert w.state == state and w.fingerprint() == stamp


def test_same_version_pack_change_requires_explicit_reselection(monkeypatch, tmp_path):
    import explainer.material_packs as packs

    w, media = work(tmp_path)
    stage_materials(w, ["library:pack.motion.typewriter@1.0"])
    props = json.loads((w.project / "props.json").read_text())
    destination = tmp_path / "catalog"
    shutil.copytree(packs.PACK_ROOT / "motion", destination / "motion")
    (destination / "index.json").write_text('["motion/manifest.json"]')
    manifest = destination / "motion/manifest.json"
    changed = json.loads(manifest.read_text())
    changed["items"][0]["purpose"] = "Changed pack description with the same published version"
    manifest.write_text(json.dumps(changed))
    monkeypatch.setattr(packs, "PACK_ROOT", destination)
    state, stamp = copy.deepcopy(w.state), w.fingerprint()
    with pytest.raises(ValueError, match="manifest"):
        w.prepare(props, media)
    assert w.state == state and w.fingerprint() == stamp


def test_staging_preflights_pruned_symlinks_before_writing_new_selection(tmp_path):
    w, _ = work(tmp_path)
    stage_materials(w, ["library:pack.phosphor.brain@1.0"])
    outside = tmp_path / "outside"
    outside.mkdir()
    (w.project / "public/library/unrelated").symlink_to(outside, target_is_directory=True)
    state = copy.deepcopy(w.state)
    stamp = w.fingerprint()
    with pytest.raises(ValueError, match="symlink"):
        stage_materials(w, ["library:pack.motion.typewriter@1.0"])
    assert w.fingerprint() == stamp and w.state == state


def test_batch_selection_validates_catalog_once(monkeypatch):
    import explainer.material_packs as packs

    original = packs.load_packs
    counted = Mock(side_effect=original)
    monkeypatch.setattr(packs, "load_packs", counted)
    selection_files(["library:pack.phosphor.book-open@1.0", "library:pack.motion.typewriter@1.0"])
    assert counted.call_count == 1


def test_receipt_creation_uses_one_verified_catalog_scan(monkeypatch):
    import explainer.material_packs as packs
    from explainer.semantic_scene import AssetRequirement
    from explainer.services.assets.library import library_receipt

    counted = Mock(side_effect=packs.load_packs)
    monkeypatch.setattr(packs, "load_packs", counted)
    receipt = library_receipt(AssetRequirement.model_validate(req()))
    assert receipt["filename"].endswith(".png") and counted.call_count == 1


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["accessors"][0].update(count=-1),
        lambda d: d["accessors"][0].update(count=0.5),
        lambda d: d["bufferViews"][0].update(byteOffset=0.5),
        lambda d: d["bufferViews"][0].update(byteLength=True),
    ],
)
def test_malformed_glb_integer_ranges_are_rejected(edit):
    raw = (ROOT / "assets/library/packs/avocado/models/Avocado.glb").read_bytes()
    size = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20 : 20 + size])
    edit(doc)
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    tail = raw[20 + size :]
    bad = (
        struct.pack("<4sII", b"glTF", 2, 20 + len(js) + len(tail))
        + struct.pack("<II", len(js), 0x4E4F534A)
        + js
        + tail
    )
    with pytest.raises(ValueError):
        validate_glb(bad)
