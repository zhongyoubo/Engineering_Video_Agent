import base64
import hashlib
import io
import json
from html import escape
import textwrap
from PIL import Image, ImageDraw, ImageFont
from fontTools import subset
from fontTools.ttLib import TTFont
from ...config import ROOT
from ...semantic_scene import AssetRequirement

FACTORY_VERSION = "component-svg-2"


def create_svg(requirement):
    """Original document/result art with a real embedded subset of the required CJK font."""
    req = AssetRequirement.model_validate(requirement)
    if req.provider != "component_svg":
        raise ValueError("Image service is not connected; no provider substitution was performed")
    texts = [req.title, *[x.text for x in req.items], *[x.detail for x in req.items]]
    if any(ord(c) < 32 and c not in "\n\t" for t in texts for c in t):
        raise ValueError("Invalid XML text")
    font_path = ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf"
    with TTFont(font_path, recalcTimestamp=False) as font:
        chars = {ord(c) for t in texts for c in t}
        if chars - set(font.getBestCmap()):
            raise ValueError("Asset text is not covered by the required font")
        options = subset.Options()
        options.recalc_timestamp = False
        reducer = subset.Subsetter(options=options)
        reducer.populate(unicodes=chars)
        reducer.subset(font)
        for record in font["name"].names:
            if record.nameID in {1, 4, 6}:
                record.string = "EVAAssetSubset".encode(record.getEncoding())
        font.flavor = "woff"
        buffer = io.BytesIO()
        font.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    license_text = escape((ROOT / "assets/fonts/LICENSE.txt").read_text())
    body = []
    y = 125
    for item in req.items:
        rows = textwrap.wrap(item.text, width=27) or [""]
        details = textwrap.wrap(item.detail, width=36)
        height = 20 + len(rows) * 48 + len(details) * 36
        fill = "#ddf0e8" if item.active else "#f0f4ef"
        body.append(f'<rect x="28" y="{y}" width="1144" height="{height}" rx="10" fill="{fill}"/>')
        for row in rows:
            body.append(f'<text x="48" y="{y + 43}" font-size="40">{escape(row)}</text>')
            y += 48
        for row in details:
            body.append(f'<text x="48" y="{y + 33}" font-size="28" fill="#526c6d">{escape(row)}</text>')
            y += 36
        y += 32
    height = y + 20
    if len(req.title) > 34:
        raise ValueError("Asset title exceeds readable header budget")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}"><metadata>{license_text}</metadata><style>@font-face{{font-family:AssetNoto;src:url(data:font/woff;base64,{encoded})}}text{{font-family:AssetNoto;fill:#183f43}}</style><rect width="1200" height="{height}" rx="20" fill="#fbfaf3"/><rect width="1200" height="80" rx="20" fill="#183f43"/><text x="28" y="51" font-size="32" style="fill:#ffffff">{escape(req.title)}</text>{"".join(body)}</svg>'''
    data = svg.encode()
    if len(data) > 800000:
        raise ValueError("Generated SVG exceeds budget")
    return data, dict(
        width=1200,
        height=height,
        format="svg",
        font="embedded original Noto subset",
        provenance="original platform code-drawn illustrative document; no actual system execution",
    )


def requirement_key(req):
    font_hash = hashlib.sha256((ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf").read_bytes()).hexdigest()
    return hashlib.sha256(
        json.dumps(
            [FACTORY_VERSION, font_hash, AssetRequirement.model_validate(req).model_dump()],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()


def create_preview(requirement):
    """Companion PNG made from the same typed input; final SVG is reviewed in real frames."""
    req = AssetRequirement.model_validate(requirement)
    height = 145 + sum(
        32 + 48 * max(1, len(textwrap.wrap(i.text, 27))) + 36 * len(textwrap.wrap(i.detail, 36))
        for i in req.items
    )
    image = Image.new("RGB", (1200, height), "#fbfaf3")
    draw = ImageDraw.Draw(image)

    def face(n):
        return ImageFont.truetype(str(ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf"), n)

    draw.rounded_rectangle((0, 0, 1199, 80), radius=20, fill="#183f43")
    draw.text((28, 14), req.title, font=face(32), fill="white")
    y = 125
    for item in req.items:
        rows = textwrap.wrap(item.text, 27) or [""]
        details = textwrap.wrap(item.detail, 36)
        h = 20 + len(rows) * 48 + len(details) * 36
        draw.rounded_rectangle((28, y, 1172, y + h), radius=10, fill="#ddf0e8" if item.active else "#f0f4ef")
        for row in rows:
            draw.text((48, y + 2), row, font=face(40), fill="#183f43")
            y += 48
        for row in details:
            draw.text((48, y + 3), row, font=face(28), fill="#526c6d")
            y += 36
        y += 32
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
