"""Structural asset consumption checks, supplemented by actual native frame review."""

from ...spatial_scene import spatial_asset_keys


def asset_usage(props):
    uses = {}
    for scene in props.get("scenes", []):
        data = scene.get("semantic_scene") or {}
        background = data.get("background_asset_key")
        if background:
            uses[scene["id"] + ":" + background] = dict(
                scene_id=scene["id"], asset_key=background, kind="background"
            )
        for entity in data.get("entities", []):
            keys = ([entity["asset_key"]] if entity.get("asset_key") else []) + spatial_asset_keys(entity)
            if not keys:
                continue
            changes = [
                e
                for e in scene.get("compiled_semantic_events", [])
                if e["target"] == entity["id"]
                and e.get("opacity", 0) is not None
                and (e.get("opacity") or 0) > 0
                and e["end_frame"] < scene["frames"]
            ]
            if entity.get("opacity", 1) <= 0 and not changes:
                raise ValueError("Registered artwork is never visible in its declared scene")
            for key in keys:
                uses[scene["id"] + ":" + key] = dict(
                    scene_id=scene["id"], asset_key=key, kind="element", entity_id=entity["id"]
                )
    return uses


def validate_generated_consumption(props, receipts, review):
    """Deployment acceptance: generated art AND transformed cutout must be scene-bound/reviewed."""
    uses = asset_usage(props)
    used = {v["asset_key"] for v in uses.values()}
    generated = {key for key, value in receipts.items() if value["request"]["provider"] == "image_service"}
    used_generated = generated & used
    backgrounds = {v["asset_key"] for v in uses.values() if v["kind"] == "background"}
    digests = {receipts[key].get("sha256") for key in used_generated}
    if len(used_generated) < 2 or len(digests - {None}) < 2 or not generated & backgrounds:
        raise ValueError("Generated artwork must be consumed by declared scenes")
    cutouts = {
        key
        for key in generated & used
        if receipts[key].get("has_alpha") and receipts[key]["request"]["transparent"]
    }
    transformed = {
        e["asset_key"]
        for s in props["scenes"]
        for e in (s.get("semantic_scene") or {}).get("entities", [])
        if e.get("asset_key") in cutouts
        and any(
            v["action"] == "transform" and v["target"] == e["id"] and v["timing_source"] == "measured_words"
            for v in s.get("compiled_semantic_events", [])
        )
    }
    if not transformed:
        raise ValueError("A generated cutout must participate in measured scene motion")
    if (
        not review
        or not review.get("accepted")
        or review.get("asset_visibility", 0) < 4
        or set(review.get("asset_expectations", [])) != set(uses)
    ):
        raise ValueError("Generated material bindings require current visual frame review")
    return uses
