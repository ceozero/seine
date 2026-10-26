# Post grade for brand renders: light shafts from a source above the frame, bloom, vignette, grain.
# python3 scripts/brand/grade.py <in.png> <out.png> <light_x_frac> <light_y_frac> [#tint]
import sys, numpy as np
from PIL import Image, ImageFilter
src, dst = sys.argv[1], sys.argv[2]; lx, ly = float(sys.argv[3]), float(sys.argv[4])  # light source (fraction of frame)
tint = sys.argv[5] if len(sys.argv) > 5 else '#D8C8FF'
im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(np.float32) / 255; h, w = a.shape[:2]
tc = np.array([int(tint[i:i + 2], 16) for i in (1, 3, 5)]) / 255
# light shafts: radial streaks from a source above the frame, broken by noise
yy, xx = np.mgrid[0:h, 0:w]; sx, sy = lx * w, ly * h
ang = np.arctan2(yy - sy, xx - sx); dist = np.hypot(xx - sx, yy - sy)
rng = np.random.default_rng(7); bands = rng.random(720)
idx = ((ang + np.pi) / (2 * np.pi) * 720).astype(int) % 720
streak = Image.fromarray((bands[idx] ** 3 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w / 300))
streak = np.asarray(streak).astype(np.float32) / 255
fall = np.clip(1 - dist / (h * 1.5), 0, 1) ** 1.6
rays = (streak * fall * 0.22)[..., None] * tc
out = 1 - (1 - a) * (1 - rays)
# bloom on bright lime/highlights
lum = out.max(axis=2); br = np.clip((lum - 0.72) / 0.28, 0, 1)[..., None] * out
b = Image.fromarray((br * 255).astype(np.uint8)); s = w / 1600
bloom = np.asarray(b.filter(ImageFilter.GaussianBlur(14 * s))).astype(np.float32) / 255 * 0.55 + np.asarray(b.filter(ImageFilter.GaussianBlur(4 * s))).astype(np.float32) / 255 * 0.3
out = 1 - (1 - out) * (1 - np.clip(bloom, 0, 1))
# vignette + fine grain
d = np.hypot((xx - w * 0.5) / (w * 0.7), (yy - h * 0.5) / (h * 0.7))
out *= (1 - 0.35 * np.clip(d - 0.45, 0, 1))[..., None]
out += (rng.standard_normal((h, w, 1)) * 0.012)
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(dst, quality=88)
