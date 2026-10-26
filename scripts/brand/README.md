# Brand asset pipeline

Rebuilds the images in `docs/assets/brand/`. See `docs/BRAND.md` for the identity.

Requirements: Blender 5.x (Cycles), Python 3 with Pillow, NumPy, cairosvg and fontTools,
and static instances of Bricolage Grotesque (OFL) at wght 800 and 500.

## 1. Render

```sh
B="blender -b --factory-startup -noaudio -P scripts/brand/net_scene.py --"
$B --out renders --style teal --variant D --name F_hero   --w 1920 --h 1080 --samples 128 --fstop 2.4 --sheet 1.5
$B --out renders --style teal --variant C --name F_banner --w 2400 --h 800  --samples 128 --tgt -2.4,0.2,-0.75 --lens 30 --fstop 5.6 --sheet 1.6
$B --out renders --style teal --variant D --name F_avatar --w 1024 --h 1024 --samples 128 --tgt 0.05,0,0 --lens 58 --fstop 2.8 --sheet 1.8
$B --out renders --style teal --variant C --name F_social --w 1280 --h 640  --samples 128 --tgt -2.3,0.2,-0.6 --lens 30 --fstop 5.6 --sheet 1.6 --skip "-4.6,-0.6"
```

Each takes under about a minute on 8 CPU threads.

## 2. Grade

```sh
python3 scripts/brand/grade.py renders/F_hero.png   renders/G_hero.png   0.3 -0.3 '#C8FFF4'
python3 scripts/brand/grade.py renders/F_banner.png renders/G_banner.png 0.7 -0.3 '#C8FFF4'
python3 scripts/brand/grade.py renders/F_avatar.png renders/G_avatar.png 0.4 -0.3 '#C8FFF4'
python3 scripts/brand/grade.py renders/F_social.png renders/G_social.png 0.7 -0.3 '#C8FFF4'
```

## 3. Build

```sh
python3 scripts/brand/assets.py \
  --font Bricolage-ExtraBold.ttf --font-text Bricolage-Medium.ttf \
  --hero renders/G_hero.png --banner renders/G_banner.png \
  --avatar renders/G_avatar.png --social renders/G_social.png
```
