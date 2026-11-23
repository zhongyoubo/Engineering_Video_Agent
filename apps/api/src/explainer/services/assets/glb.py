"""Bounded embedded glTF-2 binary validation. No remote resource resolution or execution."""

import json
import struct


def _validate_glb(data):
    if not 20 <= len(data) <= 12 * 1024 * 1024:
        raise ValueError("GLB byte budget exceeded")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Invalid GLB header")
    offset, chunks = 12, []
    while offset < length:
        if offset + 8 > length:
            raise ValueError("Truncated GLB chunk")
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size % 4 or offset + size > length:
            raise ValueError("Invalid GLB chunk range")
        chunks.append((kind, data[offset : offset + size]))
        offset += size
    if (
        len(chunks) != 2
        or [c[0] for c in chunks] != [0x4E4F534A, 0x004E4942]
        or len(chunks[0][1]) > 1024 * 1024
    ):
        raise ValueError("Require one JSON and one embedded binary GLB chunk")
    doc = json.loads(chunks[0][1].decode().rstrip(" \x00"))
    if (
        doc.get("asset", {}).get("version") != "2.0"
        or doc.get("extensionsRequired")
        or doc.get("extensionsUsed")
    ):
        raise ValueError("Only core glTF 2.0 is supported in curated model packs")
    if (
        len(doc.get("nodes", [])) > 2048
        or len(doc.get("meshes", [])) > 256
        or len(doc.get("accessors", [])) > 4096
    ):
        raise ValueError("GLB geometry budget exceeded")
    buffers = doc.get("buffers", [])
    if len(buffers) != 1 or "uri" in buffers[0] or not 0 < buffers[0]["byteLength"] <= len(chunks[1][1]):
        raise ValueError("Models must embed their buffer")
    for view in doc.get("bufferViews", []):
        if (
            view.get("buffer") != 0
            or view.get("byteOffset", 0) < 0
            or view.get("byteLength", 0) < 0
            or view.get("byteOffset", 0) + view["byteLength"] > buffers[0]["byteLength"]
        ):
            raise ValueError("Invalid embedded GLB buffer range")
    for image in doc.get("images", []):
        if (
            "uri" in image
            or image.get("mimeType") not in {"image/png", "image/jpeg"}
            or not 0 <= image.get("bufferView", -1) < len(doc.get("bufferViews", []))
        ):
            raise ValueError("GLB textures must be embedded PNG/JPEG")
    if sum(a.get("count", 0) for a in doc.get("accessors", [])) > 2000000:
        raise ValueError("GLB accessor budget exceeded")
    return dict(
        format="glb",
        nodes=len(doc.get("nodes", [])),
        meshes=len(doc.get("meshes", [])),
        binary_bytes=len(data),
    )


def validate_glb(data):
    try:
        return _validate_glb(data)
    except (KeyError, TypeError, AttributeError, UnicodeError, struct.error) as exc:
        raise ValueError("Malformed embedded GLB structure") from exc
