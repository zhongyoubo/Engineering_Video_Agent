"""Rebuild fixed curated packs from pinned upstream files. Development only, no source evaluation.

Install CairoSVG==2.8.2 separately for this maintenance command. Runtime needs only Pillow.
GLB geometry is retained; its embedded PNG/JPEG textures are resized to <=512px for previews.
"""

import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from xml.etree import ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "assets/library/packs"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def png(source, target, size):
    im = Image.open(source).convert("RGBA")
    im.thumbnail((size, size))
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    write(target, out.getvalue())


def optimize_glb(source, target):
    data = source.read_bytes()
    length, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20 : 20 + length])
    offset = 20 + length
    n, kind = struct.unpack_from("<II", data, offset)
    assert kind == 0x004E4942
    binary = data[offset + 8 : offset + 8 + n]
    images = {image["bufferView"]: image for image in doc["images"]}
    rebuilt = bytearray()
    for i, view in enumerate(doc["bufferViews"]):
        start = view.get("byteOffset", 0)
        chunk = binary[start : start + view["byteLength"]]
        if i in images:
            im = Image.open(io.BytesIO(chunk))
            im.thumbnail((512, 512))
            out = io.BytesIO()
            im.save(out, format="PNG", optimize=True)
            images[i]["mimeType"] = "image/png"
            chunk = out.getvalue()
        rebuilt.extend(b"\0" * (-len(rebuilt) % 4))
        view["byteOffset"], view["byteLength"] = len(rebuilt), len(chunk)
        rebuilt.extend(chunk)
    doc["buffers"][0]["byteLength"] = len(rebuilt)
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    rebuilt.extend(b"\0" * (-len(rebuilt) % 4))
    result = struct.pack("<III", 0x46546C67, 2, 28 + len(js) + len(rebuilt))
    result += struct.pack("<II", len(js), 0x4E4F534A) + js
    result += struct.pack("<II", len(rebuilt), 0x004E4942) + rebuilt
    write(target, result)


def main():
    if len(sys.argv) != 1:
        raise SystemExit("Fixed preparation accepts no arguments")
    import cairosvg

    sources = json.loads((PACKS / "upstream-sources.json").read_text())
    # Pin downloaded bytes as well as revision: corrupt/mismatched downloads cannot be adapted.
    for row in sources:
        p = PACKS / row["pack"] / "upstream" / row["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"]
    manifests = []
    for key, repo, revision, license_name, license_code in [
        (
            "phosphor",
            "phosphor-icons/core",
            "2b75f3ad12b420c9504ef05df8d2564a28f8500e",
            "LICENSE",
            "MIT",
        ),
        (
            "soft3d",
            "realvjy/3dicons",
            "8884d59e68a7bae0e0e2163af5b6c2ad992c01c8",
            "LICENSE",
            "CC0-1.0",
        ),
        (
            "motion",
            "lifeprompt-team/remotion-scenes",
            "02c7a84241da7010b5f59c420b0110aafd1d6f0d",
            "LICENSE",
            "MIT",
        ),
        (
            "avocado",
            "KhronosGroup/glTF-Sample-Assets",
            "e124e8d8d7330a5372bc2b4d00d39a4a9d7997ea",
            "Models/Avocado/LICENSE.md",
            "CC0-1.0 (model); CC-BY-4.0 (license metadata)",
        ),
    ]:
        folder = PACKS / key
        write(folder / "LICENSE.txt", (folder / "upstream" / license_name).read_bytes())
        items = []
        if key == "phosphor":
            labels = [
                ("book-open", "书本", ["书本", "知识", "学习"]),
                ("brain", "大脑", ["大脑", "模型", "思考"]),
                ("robot", "机器人", ["机器人", "AI", "Agent"]),
                ("terminal", "终端", ["终端", "命令行", "操作"]),
                ("folder", "文件夹", ["文件夹", "文档", "记忆"]),
                ("magnifying-glass", "放大镜", ["检索", "搜索", "RAG"]),
                ("gear", "齿轮", ["设置", "工具", "流程"]),
                ("monitor", "显示器", ["显示器", "设备", "电脑"]),
            ]
            code = [
                "/** Phosphor duotone artwork, MIT; original SVGs retained under upstream/. */",
                "import React from 'react';",
                "type IconProps = { size?: number; color?: string; opacity?: number };",
            ]
            allowed = {
                "path",
                "rect",
                "circle",
                "ellipse",
                "line",
                "polyline",
                "polygon",
                "g",
            }
            for name, label, subjects in labels:
                svg = folder / "upstream/assets/duotone" / f"{name}-duotone.svg"
                root = ET.fromstring(svg.read_bytes())
                children = []
                for child in root:
                    assert child.tag.split("}")[-1] in allowed
                    markup = ET.tostring(child, encoding="unicode")
                    markup = markup.replace("ns0:", "").replace(
                        ' xmlns:ns0="http://www.w3.org/2000/svg"', ""
                    )
                    for attr in [
                        "stroke-width",
                        "stroke-linecap",
                        "stroke-linejoin",
                        "fill-rule",
                        "clip-rule",
                    ]:
                        parts = attr.split("-")
                        markup = markup.replace(
                            attr, parts[0] + "".join(x.title() for x in parts[1:])
                        )
                    children.append(markup)
                symbol = "Pack" + "".join(x.title() for x in name.split("-"))
                code.append(
                    f'export const {symbol} = ({{size=128, color="#1c6e83", opacity=1}}: IconProps) => <svg width={{size}} height={{size}} viewBox="0 0 256 256" fill={{color}} opacity={{opacity}}>{"".join(children)}</svg>;'
                )
                preview = f"previews/{name}.png"
                root.set("fill", "#1c6e83")
                colored = ET.tostring(root)
                write(
                    folder / preview,
                    cairosvg.svg2png(
                        bytestring=colored, output_width=320, output_height=320
                    ),
                )
                items.append(
                    dict(
                        id=f"pack.phosphor.{name}",
                        name=f"双色矢量·{label}",
                        purpose=f"可辨认的{label}矢量对象，可变色/缩放，适合知识讲解和软件操作；具体含义由镜头决定。",
                        asset_type="component",
                        entry="Icons.tsx",
                        symbol=symbol,
                        preview=preview,
                        styles=["duotone", "flat", "双色", "扁平"],
                        subjects=subjects,
                        affordances=["变色", "缩放", "高亮", "路径矢量"],
                        parameters={
                            "size": "像素尺寸，默认128",
                            "color": "CSS颜色",
                            "opacity": "0..1透明度",
                        },
                    )
                )
            write(folder / "Icons.tsx", "\n".join(code) + "\n")
        elif key == "soft3d":
            for name, filename, label, subjects in [
                (
                    "notebook",
                    "notebook-dynamic-00.png",
                    "立体书本",
                    ["书本", "知识", "学习"],
                ),
                ("heart", "heart.png", "立体爱心", ["爱心", "喜欢", "反馈"]),
                ("bubble", "bubble.png", "立体对话气泡", ["对话", "问答", "聊天"]),
            ]:
                source = folder / "upstream/static" / filename
                w, h = Image.open(source).size
                png(source, folder / f"images/{name}.png", 1000)
                preview = f"previews/{name}.png"
                png(source, folder / preview, 480)
                items.append(
                    dict(
                        id=f"pack.soft3d.{name}",
                        name=label,
                        purpose=f"透明背景 PNG；原始 {w}×{h}px。"
                        + (
                            "适合小尺寸点缀，禁止冒充高分辨率主视觉。"
                            if w < 500
                            else "适合书本/知识隐喻；二维图片，不能当作三维模型旋转。"
                        ),
                        asset_type="image",
                        entry=f"images/{name}.png",
                        preview=preview,
                        styles=["soft3d", "立体插画"],
                        subjects=subjects,
                        affordances=["入场", "平移", "缩放", "透明叠加"],
                        parameters={
                            "native_size": f"{w}×{h}",
                            "rotation": "仅二维旋转",
                        },
                    )
                )
        elif key == "motion":
            for name, symbol, label in [
                ("typewriter", "PackTypewriter", "逐字输入"),
                ("kinetic", "PackKinetic", "弹性文字入场"),
            ]:
                items.append(
                    dict(
                        id=f"pack.motion.{name}",
                        name=label,
                        purpose=f"{label}，透明底、可换文本和配色；按帧确定性播放，结束保留结果。",
                        asset_type="component",
                        entry="MotionText.tsx",
                        symbol=symbol,
                        styles=["typography", "文字动效"],
                        subjects=["提示词", "终端", "观点", "标题"],
                        affordances=[
                            "逐字输入" if name == "typewriter" else "错峰弹性入场",
                            "结果停留",
                        ],
                        parameters={
                            "text": "必填文本",
                            "startFrame": "镜头局部起始帧",
                            "fontSize": "字号",
                            "color": "文字颜色",
                            "accent": "强调颜色",
                        },
                    )
                )
        else:
            optimize_glb(
                folder / "upstream/Models/Avocado/glTF-Binary/Avocado.glb",
                folder / "models/Avocado.glb",
            )
            png(
                folder / "upstream/Models/Avocado/screenshot/screenshot.jpg",
                folder / "previews/avocado.png",
                480,
            )
            items.append(
                dict(
                    id="pack.avocado.model",
                    name="牛油果三维模型",
                    purpose="Microsoft 牛油果实物 GLB；保留网格，将嵌入纹理降采样至512px。可旋转/环绕，用于说明物体观察和多模态输入，不是任意对象生成器。",
                    asset_type="model",
                    entry="models/Avocado.glb",
                    preview="previews/avocado.png",
                    styles=["textured3d", "实物三维"],
                    subjects=["牛油果", "物体观察", "多模态"],
                    affordances=["三维旋转", "镜头环绕", "材质光照"],
                    parameters={
                        "renderer": "受保护的 LibraryModel，读取 generated_assets 中的模型回执"
                    },
                )
            )
        adaptation = f"""# {key} curated adaptation\n\nSource: https://github.com/{repo}\nPinned revision: {revision}\nLicense: {license_code}. Complete upstream notice retained in LICENSE.txt.\n\nOnly enumerated files are included. No upstream executable entry point, remote font or\nnetwork loader runs in the application. Phosphor paths become parameterized React SVG.\nPNG previews are bounded derivatives, never claimed as new image inference. Motion text\nremoves fixed backgrounds, terminal badges and endless bounce; uses bundled CJK font.\nGLB keeps geometry and resizes embedded textures to 512px; original SHA is in\n../upstream-sources.json. Microsoft model credit and license metadata are retained.\n"""
        write(folder / "ADAPTATIONS.md", adaptation)
        files = []
        for p in sorted(folder.rglob("*")):
            if (
                not p.is_file()
                or p.name == "manifest.json"
                or "upstream" in p.relative_to(folder).parts
            ):
                continue
            name = str(p.relative_to(folder))
            role = (
                "license"
                if name == "LICENSE.txt"
                else "preview"
                if name.startswith("previews/")
                else "image"
                if name.startswith("images/")
                else "model"
                if name.endswith(".glb")
                else "code"
                if p.suffix == ".tsx"
                else "provenance"
            )
            files.append(
                dict(
                    path=name,
                    sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    role=role,
                )
            )
        manifest = dict(
            id=key,
            version="1.0",
            origin=f"https://github.com/{repo}",
            revision=revision,
            license=license_code,
            license_file="LICENSE.txt",
            files=files,
            items=items,
        )
        write(
            folder / "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        manifests.append(f"{key}/manifest.json")
    write(PACKS / "index.json", json.dumps(manifests, indent=2) + "\n")
    print("Prepared 4 packs / 14 material entries")


if __name__ == "__main__":
    main()
