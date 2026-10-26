import math, cairosvg, io, sys
from PIL import Image
def net_paths(cx, cy, step, bulge_r, bulge_s, n=14, ext=160):
    out = []
    for fam in (1, -1):
        for k in range(-n, n + 1):
            pts = []
            for i in range(81):
                t = -1 + 2 * i / 80
                # diamond lattice line in rotated coords
                u, v = t * ext, k * step
                x = cx + (u - fam * v) * 0.7071; y = cy + (fam * u + v) * 0.7071
                dx, dy = x - cx, y - cy; d = math.hypot(dx, dy) + 1e-6
                f = bulge_s * math.exp(-(d / bulge_r) ** 2)
                pts.append((x + dx / d * f, y + dy / d * f))
            out.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts))
    return " ".join(out)
def icon(step=16, sw=2.6, simple=False):
    cx, cy, s = 51, 53, 27
    top = f"M{cx},{cy-s} L{cx+s*0.866},{cy-s*0.5} L{cx},{cy} L{cx-s*0.866},{cy-s*0.5} Z"
    left = f"M{cx-s*0.866},{cy-s*0.5} L{cx},{cy} L{cx},{cy+s} L{cx-s*0.866},{cy+s*0.5} Z"
    right = f"M{cx+s*0.866},{cy-s*0.5} L{cx},{cy} L{cx},{cy+s} L{cx+s*0.866},{cy+s*0.5} Z"
    hexp = f"M{cx},{cy-s} L{cx+s*0.866},{cy-s*0.5} L{cx+s*0.866},{cy+s*0.5} L{cx},{cy+s} L{cx-s*0.866},{cy+s*0.5} L{cx-s*0.866},{cy-s*0.5} Z"
    net = net_paths(cx, cy, step, 34, 11, n=9)
    front = ' '.join(f'M{cx-s:.1f},{cy+o-s:.1f} L{cx+s:.1f},{cy+o+s:.1f}' for o in (-9, 9))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1BA3A0"/><stop offset="1" stop-color="#05333A"/></linearGradient>
<radialGradient id="gl" cx="{cx}" cy="{cy}" r="30" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#AAFF00" stop-opacity="0.35"/><stop offset="1" stop-color="#AAFF00" stop-opacity="0"/></radialGradient>
<clipPath id="tile"><rect width="100" height="100" rx="23"/></clipPath><clipPath id="hx"><path d="{hexp}"/></clipPath></defs>
<g clip-path="url(#tile)"><rect width="100" height="100" fill="url(#g)"/><rect width="100" height="100" fill="url(#gl)"/>
{'' if simple else f'<path d="{net}" fill="none" stroke="#DFFBF6" stroke-width="{sw}" stroke-linecap="round" opacity="0.8"/>'}
<path d="{top}" fill="#D8FF6E"/><path d="{left}" fill="#AAFF00"/><path d="{right}" fill="#7CCF00"/>
<g clip-path="url(#hx)"><path d="{front}" fill="none" stroke="#F2FFFB" stroke-width="{sw*1.15}" stroke-linecap="round"/></g>
</g></svg>'''
if __name__ == "__main__":
    out = sys.argv[1]
    open(out + "/icon.svg", "w").write(icon())
    open(out + "/icon-simple.svg", "w").write(icon(simple=True))
    sheet = Image.new("RGB", (900, 330), "#E9EEED")
    for i, (name, sz) in enumerate((("icon.svg", 256), ("icon.svg", 64), ("icon.svg", 32), ("icon.svg", 16), ("icon-simple.svg", 64), ("icon-simple.svg", 32), ("icon-simple.svg", 16))):
        im = Image.open(io.BytesIO(cairosvg.svg2png(url=out + "/" + name, output_width=sz))).convert("RGBA")
        x = [20, 300, 390, 450, 520, 610, 670][i]; sheet.paste(im, (x, 40), im)
    sheet.save(out + "/icon_sheet.png")
