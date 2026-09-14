"""Regenerates every CareerOS brand raster from the official brand board.

Source of truth: .claude/skills/careeros-ui-system/assets/brand-reference/careeros-brand-board.png
(the owner-supplied Logos.png: primary logo, symbol, app icon). The artwork only exists as that
raster, so this script cuts the symbol and wordmark out of it with clean transparency and derives
every platform asset from those cut-outs:

  - Brand masters (skill brand-reference): symbol / wordmark, full colour and on-dark, app icon
  - Flutter assets (mobile/assets/brand, 1x/2x/3x): symbol + wordmark, full colour and on-dark
  - Android: adaptive icon layers + monochrome, legacy launcher icons, launch-window logo
  - iOS: AppIcon set, LaunchImage
  - Admin: public/brand cut-outs, app/icon.png, app/apple-icon.png

On-dark variants follow the board's app icon: the navy C becomes white; ribbon, arrow and spark
keep their blues. If a vector or larger export of the logo becomes available, replace the board
and the crop boxes below — nothing else needs to change.

Usage (needs Pillow; the backend venv has it):
    python mobile/tool/generate_brand_assets.py [path/to/board.png]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

MOBILE = Path(__file__).resolve().parents[1]
REPO = MOBILE.parent
BRAND_REFERENCE = REPO / ".claude/skills/careeros-ui-system/assets/brand-reference"
DEFAULT_BOARD = BRAND_REFERENCE / "careeros-brand-board.png"

FLUTTER_BRAND = MOBILE / "assets/brand"
ANDROID_RES = MOBILE / "android/app/src/main/res"
IOS_ICONS = MOBILE / "ios/Runner/Assets.xcassets/AppIcon.appiconset"
IOS_LAUNCH = MOBILE / "ios/Runner/Assets.xcassets/LaunchImage.imageset"
ADMIN = REPO / "admin"

# Tight bounding boxes on the 1448×1086 board (large primary logo).
SYMBOL_BOX = (497, 74, 1011, 523)
WORDMARK_BOX = (330, 537, 1117, 665)
PAD = 4

# Where the C's gradient turns bright blue near its upper terminal (symbol cut-out coordinates,
# including PAD). Pixels here belong to the C even though their blue channel looks like ribbon.
C_TERMINAL_ZONE = (289, 24, 394, 109)

WHITE = (255, 255, 255)
# App icon ground, sampled from the board's app icon: bright blue glow top-right into deep navy.
ICON_GLOW = (0, 84, 180)
ICON_MID = (4, 40, 92)
ICON_DEEP = (3, 23, 60)

# Icon composition (fractions of the icon edge), matched to the board's app icon.
ICON_SYMBOL_WIDTH = 0.72
ICON_SYMBOL_CENTER = (0.51, 0.47)


# --------------------------------------------------------------------------------------------------
# Cut-out
# --------------------------------------------------------------------------------------------------


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def cut_out(board: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Removes the near-white board background, un-mixing anti-aliased edges.

    Every colour in the logo has a red channel near 0 while the ground is ~254, so red measures
    coverage precisely: alpha = (ground - R) / (ground - R_foreground), with R_foreground taken
    from the darkest red nearby (a min filter), then the foreground colour is recovered from the
    compositing equation. Faint glow with no real foreground nearby is dropped.
    """
    x0, y0, x1, y1 = box[0] - PAD, box[1] - PAD, box[2] + PAD, box[3] + PAD
    rgb = board.convert("RGB").crop((x0, y0, x1, y1))
    w, h = rgb.size

    border = [rgb.getpixel((x, 0)) for x in range(w)] + [rgb.getpixel((x, h - 1)) for x in range(w)]
    ground = tuple(round(sum(p[i] for p in border) / len(border)) for i in range(3))

    near_red = rgb.getchannel("R").filter(ImageFilter.MinFilter(7)).load()
    src = rgb.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            c = src[x, y]
            coverage = max(ground[i] - c[i] for i in range(3))
            if coverage < 4:
                continue
            span = ground[0] - near_red[x, y]
            if coverage >= 150:
                alpha = 1.0
            elif span < 120:
                continue
            else:
                alpha = min(max((ground[0] - c[0]) / span, 0.0), 1.0)
            if alpha < 0.03:
                continue
            fg = tuple(
                round(min(max((c[i] - (1 - alpha) * ground[i]) / alpha, 0), 255)) for i in range(3)
            )
            dst[x, y] = (*fg, round(alpha * 255))
    return out


def on_dark(image: Image.Image, *, ribbon_from: float, ribbon_full: float, keep_zone=None) -> Image.Image:
    """Navy → white; blues (blue channel ≥ ribbon_full) keep their colour; blends in between.

    The ribbon's shaded fold inside the C is as dark as the C's brighter end, but far less green
    (G/B ≈ 0.3 vs ≥ 0.4 across the C), so low G/B also counts as ribbon.
    """
    out = image.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if keep_zone and keep_zone[0] <= x < keep_zone[2] and keep_zone[1] <= y < keep_zone[3]:
                t = 0.0
            else:
                t = _smoothstep(ribbon_from, ribbon_full, b)
                if b >= 120:
                    t = max(t, _smoothstep(0.40, 0.34, g / b) * _smoothstep(120, 150, b))
            px[x, y] = (
                round(WHITE[0] + (r - WHITE[0]) * t),
                round(WHITE[1] + (g - WHITE[1]) * t),
                round(WHITE[2] + (b - WHITE[2]) * t),
                a,
            )
    return out


def silhouette(image: Image.Image) -> Image.Image:
    out = Image.new("RGBA", image.size, (*WHITE, 0))
    out.putalpha(image.getchannel("A"))
    return out


def resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Premultiplied resampling so edges never pick up dark or white fringes."""
    size = (max(1, round(size[0])), max(1, round(size[1])))
    scaled = image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    if size[0] > image.size[0]:
        # The board is the only source; soften the upscale softness on the largest icons.
        rgb = scaled.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
        rgb.putalpha(scaled.getchannel("A"))
        scaled = rgb
    return scaled


def fit_width(image: Image.Image, width: float) -> Image.Image:
    return resize(image, (width, width * image.size[1] / image.size[0]))


# --------------------------------------------------------------------------------------------------
# Icons
# --------------------------------------------------------------------------------------------------


def icon_ground(size: int) -> Image.Image:
    """The board's app-icon ground: a soft glow from the top-right corner falling into deep navy."""
    master = 256
    img = Image.new("RGB", (master, master))
    px = img.load()
    for y in range(master):
        for x in range(master):
            u, v = x / (master - 1), y / (master - 1)
            d = math.hypot((1 - u) * 0.85, v)
            t = _smoothstep(0.0, 1.15, d)
            if t < 0.45:
                k = t / 0.45
                c = [ICON_GLOW[i] + (ICON_MID[i] - ICON_GLOW[i]) * k for i in range(3)]
            else:
                k = (t - 0.45) / 0.55
                c = [ICON_MID[i] + (ICON_DEEP[i] - ICON_MID[i]) * k for i in range(3)]
            px[x, y] = tuple(round(ch) for ch in c)
    return img.resize((size, size), Image.Resampling.BICUBIC)


def place(canvas: Image.Image, symbol: Image.Image, width: float, center: tuple[float, float]) -> None:
    mark = fit_width(symbol, width)
    cx, cy = center[0] * canvas.size[0], center[1] * canvas.size[1]
    canvas.alpha_composite(mark, (round(cx - mark.size[0] / 2), round(cy - mark.size[1] / 2)))


def app_icon(size: int, symbol_on_dark: Image.Image, *, shape: str = "square", symbol_width: float = ICON_SYMBOL_WIDTH) -> Image.Image:
    """shape: 'square' (opaque, full-bleed: iOS/stores), 'rounded' (legacy Android, admin favicon), 'circle'."""
    canvas = icon_ground(size).convert("RGBA")
    place(canvas, symbol_on_dark, size * symbol_width, ICON_SYMBOL_CENTER if shape != "circle" else (0.5, 0.5))
    if shape == "square":
        return canvas.convert("RGB")
    ss = 4
    mask = Image.new("L", (size * ss, size * ss), 0)
    draw = ImageDraw.Draw(mask)
    if shape == "circle":
        draw.ellipse([0, 0, size * ss - 1, size * ss - 1], fill=255)
    else:
        draw.rounded_rectangle([0, 0, size * ss - 1, size * ss - 1], radius=round(size * ss * 0.22), fill=255)
    canvas.putalpha(mask.resize((size, size), Image.Resampling.LANCZOS))
    return canvas


def save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


# --------------------------------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------------------------------


def main() -> None:
    board_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BOARD
    board = Image.open(board_path)
    if board.size != (1448, 1086):
        raise SystemExit(f"Unexpected board size {board.size}; update SYMBOL_BOX / WORDMARK_BOX for the new artwork.")

    symbol = cut_out(board, SYMBOL_BOX)
    symbol_dark = on_dark(symbol, ribbon_from=150, ribbon_full=185, keep_zone=C_TERMINAL_ZONE)
    wordmark = cut_out(board, WORDMARK_BOX)
    wordmark_dark = on_dark(wordmark, ribbon_from=150, ribbon_full=220)

    # Brand masters (native resolution).
    save(symbol, BRAND_REFERENCE / "careeros-symbol.png")
    save(symbol_dark, BRAND_REFERENCE / "careeros-symbol-on-dark.png")
    save(wordmark, BRAND_REFERENCE / "careeros-wordmark.png")
    save(wordmark_dark, BRAND_REFERENCE / "careeros-wordmark-on-dark.png")
    save(app_icon(1024, symbol_dark), BRAND_REFERENCE / "careeros-app-icon.png")

    # Flutter: native cut-out is the 3.0x variant.
    for name, image in {
        "careeros_symbol.png": symbol,
        "careeros_symbol_on_dark.png": symbol_dark,
        "careeros_wordmark.png": wordmark,
        "careeros_wordmark_on_dark.png": wordmark_dark,
    }.items():
        save(image, FLUTTER_BRAND / "3.0x" / name)
        save(fit_width(image, image.size[0] * 2 / 3), FLUTTER_BRAND / "2.0x" / name)
        save(fit_width(image, image.size[0] / 3), FLUTTER_BRAND / name)

    # Android. Adaptive icon layers are 108dp; the symbol stays inside the 66dp safe circle.
    densities = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
    for density, scale in densities.items():
        mipmap = ANDROID_RES / f"mipmap-{density}"
        legacy = round(48 * scale)
        save(app_icon(legacy, symbol_dark, shape="rounded"), mipmap / "ic_launcher.png")
        save(app_icon(legacy, symbol_dark, shape="circle", symbol_width=0.62), mipmap / "ic_launcher_round.png")

        layer = round(108 * scale)
        save(icon_ground(layer), mipmap / "ic_launcher_background.png")
        foreground = Image.new("RGBA", (layer, layer), (0, 0, 0, 0))
        place(foreground, symbol_dark, layer * 50 / 108, (0.5, 0.5))
        save(foreground, mipmap / "ic_launcher_foreground.png")
        monochrome = Image.new("RGBA", (layer, layer), (0, 0, 0, 0))
        place(monochrome, silhouette(symbol), layer * 50 / 108, (0.5, 0.5))
        save(monochrome, mipmap / "ic_launcher_monochrome.png")

        # Launch window (Android 7–11): on-dark symbol, 112dp wide, centred on navy.
        save(fit_width(symbol_dark, 112 * scale), ANDROID_RES / f"drawable-{density}" / "splash_logo.png")

    # iOS.
    contents = json.loads((IOS_ICONS / "Contents.json").read_text())
    for entry in contents["images"]:
        filename = entry.get("filename")
        if not filename:
            continue
        points = float(entry["size"].split("x")[0])
        factor = int(entry["scale"].rstrip("x"))
        save(app_icon(round(points * factor), symbol_dark), IOS_ICONS / filename)
    for suffix, factor in (("", 1), ("@2x", 2), ("@3x", 3)):
        save(fit_width(symbol_dark, 112 * factor), IOS_LAUNCH / f"LaunchImage{suffix}.png")

    # Admin.
    save(symbol, ADMIN / "public/brand/careeros-symbol.png")
    save(symbol_dark, ADMIN / "public/brand/careeros-symbol-on-dark.png")
    save(wordmark, ADMIN / "public/brand/careeros-wordmark.png")
    save(wordmark_dark, ADMIN / "public/brand/careeros-wordmark-on-dark.png")
    save(app_icon(512, symbol_dark, shape="rounded"), ADMIN / "app/icon.png")
    save(app_icon(180, symbol_dark), ADMIN / "app/apple-icon.png")

    print(f"symbol {symbol.size}, wordmark {wordmark.size}")
    print("Brand assets regenerated.")


if __name__ == "__main__":
    main()
