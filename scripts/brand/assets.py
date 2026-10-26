#!/usr/bin/env python3
"""Build seine brand assets into docs/assets/brand from the flat icon and the graded renders.

    python3 scripts/brand/assets.py --font Bricolage-ExtraBold.ttf --font-text Bricolage-Medium.ttf \
        --hero hero.png --banner banner.png --avatar avatar.png \
        --social social.png

Renders come from scripts/brand/net_scene.py (Blender) graded by scripts/brand/grade.py; see docs/BRAND.md.
Fonts: Bricolage Grotesque (OFL), static instances at wght 800 (wordmark) and 500 (tagline).
"""

import argparse
import io
import sys
from pathlib import Path

import cairosvg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon import icon  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs/assets/brand"

ABYSS = "#021A1E"
DEEP = "#063B44"
TEAL = "#1BA3A0"
FOAM = "#DFFBF6"
LIME = "#AAFF00"
LIME_ON_LIGHT = "#4E9A00"
TAGLINE = "The fastest Blocknet miner"


def text_path(font, text, x, y, size, tracking=0.0):
    """Outline `text` with its baseline at (x, y); returns (path_d, advance_width)."""
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    s = size / upm
    pen = SVGPathPen(gs)
    cursor = 0.0
    for ch in text:
        g = cmap[ord(ch)]
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x + cursor, y)))
        cursor += gs[g].width * s + tracking
    return pen.getCommands(), cursor - tracking


def wordmark_svg(font, x, y, size, ink, dot):
    """'seine.' with the full stop in lime."""
    d, w = text_path(font, "seine", x, y, size, tracking=-0.035 * size)
    dd, dw = text_path(font, ".", x + w - 0.01 * size, y, size)
    return f'<path d="{d}" fill="{ink}"/><path d="{dd}" fill="{dot}"/>', w + dw


def lockup(font, ink, dot, ground=None):
    h = 140
    icon_svg = icon().replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">', "").replace("</svg>", "")
    icon_svg = icon_svg.replace('id="g"', 'id="lg"').replace("url(#g)", "url(#lg)")
    wm, w = wordmark_svg(font, 148, 98, 92, ink, dot)
    width = 148 + w + 36
    bg = f'<rect width="{width:.0f}" height="{h}" rx="26" fill="{ground}"/>' if ground else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {h}">{bg}'
            f'<g transform="translate(18 18) scale(1.04)">{icon_svg}</g>{wm}</svg>')


def overlay_text(img, font_bold, font_text, x, y, size, tagline_size, shadow=True, up=0.0, down=0.0):
    """Bake the 'seine.' wordmark and tagline onto a raster with a soft shadow."""
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fb = ImageFont.truetype(font_bold, size)
    ft = ImageFont.truetype(font_text, tagline_size)
    word_w = d.textlength("seine", font=fb)
    word_w -= 0.035 * size * 4
    # frosted panel: blur and darken the net behind the type, feathered into the image
    tag_w = d.textlength(TAGLINE, font=ft)
    pad = size * 0.45
    x0, y0 = int(x - pad), int(y - pad * 0.55)
    x1, y1 = int(x + max(word_w + size * 0.6, tag_w) + pad), int(y + size * 1.12 + tagline_size * 1.6 + pad * 0.7)
    y0, y1 = int(y0 - size * up), int(y1 + size * down)
    blurred = img.filter(ImageFilter.GaussianBlur(size * 0.025))
    tint = Image.new("RGBA", img.size, (2, 26, 30, 44))
    frosted = Image.alpha_composite(blurred, tint)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), radius=int(size * 0.3), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size * 0.65))
    img = Image.composite(frosted, img, mask)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.text((x, y), "seine.", font=fb, fill=(0, 10, 14, 170))
        sd.text((x + size * 0.04, y + size * 1.12), TAGLINE, font=ft, fill=(0, 10, 14, 170))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(size * 0.18)))
    cursor = x
    for ch in "seine":
        d.text((cursor, y), ch, font=fb, fill=FOAM)
        cursor += d.textlength(ch, font=fb) - 0.035 * size
    d.text((cursor, y), ".", font=fb, fill=LIME)
    d.text((x + size * 0.04, y + size * 1.12), TAGLINE, font=ft, fill="#CDEDE8")
    return Image.alpha_composite(img, layer)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--font", required=True, help="Bricolage Grotesque ExtraBold (static instance)")
    ap.add_argument("--font-text", required=True, help="Bricolage Grotesque Medium (static instance)")
    ap.add_argument("--hero", required=True)
    ap.add_argument("--banner", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--social", required=True, help="2:1 render for the social card")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    font = TTFont(args.font)

    svgs = {
        "icon.svg": icon(),
        "icon-simple.svg": icon(simple=True),
        "lockup-dark.svg": lockup(font, FOAM, LIME),
        "lockup-light.svg": lockup(font, DEEP, LIME_ON_LIGHT),
        "lockup-card.svg": lockup(font, FOAM, LIME, ground=ABYSS),
    }
    for name, svg in svgs.items():
        (OUT / name).write_text(svg + "\n")
    for size, src in ((512, "icon.svg"), (180, "icon.svg"), (32, "icon-simple.svg"), (16, "icon-simple.svg")):
        png = cairosvg.svg2png(bytestring=svgs[src].encode(), output_width=size)
        Image.open(io.BytesIO(png)).save(OUT / f"icon-{size}.png")

    # README banner: 3:1, wordmark in the open net on the left
    b = Image.open(args.banner).convert("RGBA").resize((1800, 600), Image.LANCZOS)
    b = overlay_text(b, args.font, args.font_text, 96, 196, 150, 40, up=1.0, down=0.35)
    b.convert("RGB").save(OUT / "banner.jpg", quality=88, optimize=True, progressive=True)

    # social card: 1280x640 render with the wordmark in the open net on the left
    card = Image.open(args.social).convert("RGBA").resize((1280, 640), Image.LANCZOS)
    card = overlay_text(card, args.font, args.font_text, 72, 170, 120, 28, up=1.0, down=0.35)
    card.convert("RGB").save(OUT / "social-card.jpg", quality=88, optimize=True, progressive=True)

    # avatar: square render, 512
    Image.open(args.avatar).convert("RGB").resize((512, 512), Image.LANCZOS).save(OUT / "avatar.png", optimize=True)
    for p in sorted(OUT.iterdir()):
        print(p.relative_to(ROOT), p.stat().st_size)


if __name__ == "__main__":
    main()
