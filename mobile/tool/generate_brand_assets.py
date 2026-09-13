"""Regenerates CareerOS raster brand assets from the pathway-mark geometry.

Source of truth for the geometry: .claude/skills/careeros-ui-system/assets/brand-reference/careeros-mark.svg
(mirrored by CareerOSMark in lib/core/widgets/careeros_logo.dart). Vector surfaces (Android adaptive
icon foreground, Android splash, admin favicon) are hand-written SVG/VectorDrawable and don't need
this script; it only produces PNGs that platforms require:

  - Android legacy launcher icons (API 24-25): mipmap-*/ic_launcher.png, ic_launcher_round.png
  - iOS AppIcon set (opaque, full-bleed)
  - iOS LaunchImage (reversed mark, transparent, on the navy launch screen)

Usage (needs Pillow; the backend venv has it):
    python mobile/tool/generate_brand_assets.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android/app/src/main/res"
IOS_ICONS = ROOT / "ios/Runner/Assets.xcassets/AppIcon.appiconset"
IOS_LAUNCH = ROOT / "ios/Runner/Assets.xcassets/LaunchImage.imageset"

NAVY = (7, 26, 56)
NAVY_LIGHT = (11, 37, 80)
BLUE = (22, 119, 255)
BRIGHT_BLUE = (36, 155, 255)
CYAN = (19, 189, 235)
WHITE = (255, 255, 255)

SUPERSAMPLE = 4


def _gradient(size: tuple[int, int], start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    """Diagonal gradient: `start` at bottom-left, `end` at top-right (matches the SVG x1=0 y1=1 x2=1 y2=0)."""
    w, h = max(size[0], 1), max(size[1], 1)
    # linear_gradient is black at the top; rotating 90° counter-clockwise puts black on the left.
    horizontal = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))
    vertical_up = ImageChops.invert(Image.linear_gradient("L").resize((w, h)))
    t = Image.blend(horizontal, vertical_up, 0.5)
    return Image.composite(Image.new("RGB", (w, h), end), Image.new("RGB", (w, h), start), t)


def _cubic(p0, p1, p2, p3, steps=64):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _paste_gradient(canvas: Image.Image, mask: Image.Image, colors) -> None:
    box = mask.getbbox()
    if not box:
        return
    grad = _gradient((box[2] - box[0], box[3] - box[1]), *colors)
    canvas.paste(grad, box[:2], mask.crop(box))


def draw_mark(canvas: Image.Image, origin: tuple[float, float], scale: float, *, reversed_: bool) -> None:
    """Draws the 64-unit mark onto `canvas` (RGBA) at `origin` with `scale` pixels per unit."""
    ox, oy = origin

    def p(x, y):
        return (ox + x * scale, oy + y * scale)

    draw = ImageDraw.Draw(canvas)

    # C: arc through (49.5,17.5) -> (53,41), r=22, large-arc, counter-clockwise. Centre solved from
    # the SVG arc parameters.
    cx, cy, r = 32.93, 31.98, 22.0
    stroke = 8.5
    start_deg = math.degrees(math.atan2(41 - cy, 53 - cx))
    end_deg = math.degrees(math.atan2(17.5 - cy, 49.5 - cx)) + 360
    outer = r + stroke / 2
    c_color = WHITE if reversed_ else NAVY
    draw.arc([p(cx - outer, cy - outer), p(cx + outer, cy + outer)], start_deg, end_deg, fill=c_color, width=round(stroke * scale))
    for ex, ey in ((49.5, 17.5), (53, 41)):
        rr = stroke / 2 * scale
        x, y = p(ex, ey)
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c_color)

    gradient_colors = (BRIGHT_BLUE, CYAN) if reversed_ else (BLUE, CYAN)

    # Pathway
    path_mask = Image.new("L", canvas.size, 0)
    pm = ImageDraw.Draw(path_mask)
    # Stamp discs densely along the curve: a round-capped stroke without the seam artifacts that
    # ImageDraw.line's per-segment joins leave on tight curves.
    rr = 6.5 / 2 * scale
    for x, y in (p(x, y) for x, y in _cubic((17, 44), (27, 44), (34, 38), (44.5, 27.5), steps=int(120 * scale))):
        pm.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    _paste_gradient(canvas, path_mask, gradient_colors)

    # Arrowhead (polygon + 2-unit rounded stroke)
    arrow_mask = Image.new("L", canvas.size, 0)
    am = ImageDraw.Draw(arrow_mask)
    tri = [p(57, 15), p(51.6, 32.4), p(39.6, 20.4)]
    am.polygon(tri, fill=255)
    am.line(tri + [tri[0]], fill=255, width=round(2 * scale), joint="curve")
    for x, y in tri:
        rr = scale
        am.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    _paste_gradient(canvas, arrow_mask, gradient_colors)

    # Spark
    spark = [(58, 4), (59.4, 7.6), (63, 9), (59.4, 10.4), (58, 14), (56.6, 10.4), (53, 9), (56.6, 7.6)]
    draw.polygon([p(x, y) for x, y in spark], fill=CYAN)


def render_icon(size: int, *, shape: str) -> Image.Image:
    """shape: 'square' (opaque full-bleed, iOS), 'rounded' (legacy Android), 'circle' (legacy round)."""
    big = size * SUPERSAMPLE
    background = _gradient((big, big), NAVY, NAVY_LIGHT).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    canvas = background.convert("RGBA")
    # Mark occupies 62.5% of the icon (inside the 66% adaptive safe zone), centred.
    mark_px = big * 0.625
    draw_mark(canvas, ((big - mark_px) / 2, (big - mark_px) / 2), mark_px / 64, reversed_=True)

    if shape != "square":
        mask = Image.new("L", (big, big), 0)
        md = ImageDraw.Draw(mask)
        if shape == "circle":
            md.ellipse([0, 0, big - 1, big - 1], fill=255)
        else:
            md.rounded_rectangle([0, 0, big - 1, big - 1], radius=round(big * 0.22), fill=255)
        canvas.putalpha(mask)

    image = canvas.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB") if shape == "square" else image


def render_launch_mark(size: int) -> Image.Image:
    big = size * SUPERSAMPLE
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw_mark(canvas, (0, 0), big / 64, reversed_=True)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    densities = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    for density, px in densities.items():
        folder = ANDROID_RES / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        render_icon(px, shape="rounded").save(folder / "ic_launcher.png", optimize=True)
        render_icon(px, shape="circle").save(folder / "ic_launcher_round.png", optimize=True)

    contents = json.loads((IOS_ICONS / "Contents.json").read_text())
    for entry in contents["images"]:
        filename = entry.get("filename")
        if not filename:
            continue
        points = float(entry["size"].split("x")[0])
        factor = int(entry["scale"].rstrip("x"))
        render_icon(round(points * factor), shape="square").save(IOS_ICONS / filename, optimize=True)

    for suffix, factor in (("", 1), ("@2x", 2), ("@3x", 3)):
        render_launch_mark(96 * factor).save(IOS_LAUNCH / f"LaunchImage{suffix}.png", optimize=True)

    print("Brand assets regenerated.")


if __name__ == "__main__":
    main()
