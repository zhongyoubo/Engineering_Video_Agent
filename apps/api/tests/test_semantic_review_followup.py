"""Regressions found by the semantic-production deployment/recovery review."""

import hashlib
import json
from pathlib import PurePosixPath
import re
import shlex

import pytest

from explainer.config import ROOT
from explainer.services.assets.registry import request_assets, restore_assets
from explainer.services.render_plan import build_render_plan
from test_semantic_scenes import workspace, requirement, scene


def test_render_image_packages_transitive_local_runtime_imports():
    """Check real image COPY inputs, rather than assuming host imports match the image."""
    packaged = {}
    for line in (ROOT / "infra/engineering-render/Dockerfile").read_text().splitlines():
        if not line.startswith("COPY "):
            continue
        args = shlex.split(line)[1:]
        destination = PurePosixPath(args[-1])
        for src in args[:-1]:
            files = list(ROOT.glob(src))
            assert files, src
            for file in files:
                target = destination / file.name if args[-1].endswith("/") else destination
                packaged[str(target)] = file
    assert "render.mjs" in packaged
    for target, source in packaged.items():
        if source.suffix != ".mjs":
            continue
        for imported in re.findall(r"(?:from\s*|import\s*)['\"](\./[^'\"]+)['\"]", source.read_text()):
            resolved = str(PurePosixPath(target).parent / imported)
            assert resolved in packaged, f"{target} imports {imported}, missing from render image"


def test_recovered_cache_cannot_republish_corrupt_svg(tmp_path):
    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    receipt = w.state["generated_assets"]["result"]
    expected = receipt["sha256"]
    receipt["svg"] = '<svg xmlns="http://www.w3.org/2000/svg"><text>corrupt cache</text></svg>'
    receipt["preview_png"] = "corrupt cached preview"
    restore_assets(w)
    request_assets(w, [requirement()], lambda: None)
    restored = w.state["generated_assets"]["result"]
    actual = (w.project / "public" / restored["filename"]).read_bytes()
    assert hashlib.sha256(actual).hexdigest() == expected
    assert restored["svg"].encode() == actual


def test_repeated_asset_request_preserves_exact_current_acceptance(tmp_path):
    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    stamp = w.fingerprint()
    w.state.update(build_hash=stamp, preview_hash=stamp, review_hash=stamp, finished=True)
    w.state["frames"] = [{"name": "inspected-frame.png"}]
    request_assets(w, [requirement()], lambda: None)
    assert w.fingerprint() == stamp
    assert all(w.state[k] == stamp for k in ["build_hash", "preview_hash", "review_hash"])
    assert w.state["finished"] and w.state["frames"]


def test_recovery_validates_the_entire_batch_before_writing(tmp_path):
    w = workspace(tmp_path)
    a, b = requirement(), requirement().model_copy(update={"id": "other"})
    request_assets(w, [a, b], lambda: None)
    first = w.project / "public" / w.state["generated_assets"]["result"]["filename"]
    first.unlink()
    w.state["generated_assets"]["other"]["preview_sha256"] = "invalid"
    with pytest.raises(ValueError):
        restore_assets(w)
    assert not first.exists()


@pytest.mark.parametrize(
    "field,value", [("accent", "amber"), ("design_pack", "editorial_warm"), ("fontSrc", "different.otf")]
)
def test_scene_dependencies_include_presentation_props(tmp_path, field, value):
    s = scene().model_dump()
    public = tmp_path / "public"
    public.mkdir()
    props = dict(scenes=[s], width=1920, height=1080, accent="blue", design_pack="workspace_tech")
    original = build_render_plan(props, public)
    changed = build_render_plan({**props, field: value}, public)
    assert original["scenes"][0]["dependency_key"] != changed["scenes"][0]["dependency_key"]
    # The manifest must not hash itself recursively when refreshed.
    assert build_render_plan({**props, "render_plan": original}, public) == original
    json.dumps(changed)


def test_large_bounded_preview_receipt_and_oversized_rejection(tmp_path):
    from explainer.services.engineering.tools import read_receipt
    from explainer.services.engineering.workspace import EngineeringError

    payload = dict(
        protocol="3.0",
        action="preview",
        ok=True,
        frames=[dict(name=f"frame-{i:06}.png", frame=i) for i in range(128)],
        clips=[
            dict(
                name=f"motion-{i:03}-0.mp4",
                scene_id="scene_" + "s" * 50 + str(i % 32),
                start_frame=i * 150,
                end_frame=i * 150 + 120,
            )
            for i in range(80)
        ],
        motion_frames=[
            dict(name=f"motion-{i:03}-0.png", frame=i * 150, kind="motion_strip") for i in range(80)
        ],
    )
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload))
    assert path.stat().st_size > 20000  # Protocol-bounded frame/clip lists can exceed the old aggregate parser cap.
    assert read_receipt(path, "preview") == payload
    path.write_text(" " * (128 * 1024 + 1))
    with pytest.raises(EngineeringError, match="receipt"):
        read_receipt(path, "preview")


@pytest.mark.parametrize("change", ["range", "type", "fps", "frame_count", "duration", "missing_stream"])
def test_continuous_clip_metadata_must_match_declared_range(change):
    from explainer.services.engineering.tools import validate_motion_clip
    from explainer.services.engineering.workspace import EngineeringError

    item = dict(scene_id="s", start_frame=110, end_frame=139)
    s = dict(id="s", start_frame=100, frames=200)
    metadata = dict(
        streams=[dict(codec_type="video", width=1280, height=720, avg_frame_rate="30/1", nb_frames="30")],
        format=dict(duration="1.0"),
    )
    validate_motion_clip(item, s, metadata, 30)
    if change == "range":
        item["start_frame"] = 99
    if change == "type":
        item["end_frame"] = "139"
    if change == "fps":
        metadata["streams"][0]["avg_frame_rate"] = "60/1"
    if change == "frame_count":
        item["end_frame"] = 249
    if change == "duration":
        metadata["format"]["duration"] = "0.1"
    if change == "missing_stream":
        metadata["streams"] = []
    with pytest.raises(EngineeringError):
        validate_motion_clip(item, s, metadata, 30)


def test_corrupt_in_memory_cache_is_rejected_before_publication(tmp_path):
    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    prior = w.fingerprint()
    w.state["generated_assets"]["result"]["svg"] = "corrupt cached bytes"
    with pytest.raises(ValueError, match="inconsistent"):
        request_assets(w, [requirement()], lambda: None)
    assert w.fingerprint() == prior


def test_asset_io_failure_cannot_leave_acceptance_on_modified_files(tmp_path, monkeypatch):
    from explainer.services import render_plan

    w = workspace(tmp_path)
    request_assets(w, [requirement()], lambda: None)
    stamp = w.fingerprint()
    w.state.update(build_hash=stamp, preview_hash=stamp, review_hash=stamp, finished=True)

    def fail(_):
        raise OSError("simulated disk failure during manifest publication")

    monkeypatch.setattr(render_plan, "refresh_plan", fail)
    with pytest.raises(OSError):
        request_assets(w, [requirement().model_copy(update={"title": "新结果"})], lambda: None)
    assert w.fingerprint() != stamp
    assert all(w.state[k] is None for k in ["build_hash", "preview_hash", "review_hash"])
    assert not w.state["finished"]
