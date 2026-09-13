"""Generates original, locally-rendered abstract-reasoning images for demo seed data (Phase 7.5
spec §18). Every image is drawn procedurally with Pillow — no downloaded or copyrighted
commercial aptitude-test content — and saved directly into the backend's local upload directory
so it's served at the same `/uploads/<file>` URL the admin upload pipeline produces.

Usage:
    cd backend && python -m scripts.generate_abstract_images
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

from app.core.config import get_settings

CANVAS = 300
BG = (255, 255, 255)
INK = (16, 33, 61)  # AppColors.text
ACCENT = (22, 119, 255)  # AppColors.blue
MUTED = (113, 128, 150)  # AppColors.muted


def _output_dir() -> Path:
    settings = get_settings()
    directory = Path(settings.upload_dir) / "abstract"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (CANVAS, CANVAS), BG)
    return image, ImageDraw.Draw(image)


def _save(image: Image.Image, name: str) -> str:
    path = _output_dir() / f"{name}.png"
    image.save(path, format="PNG")
    return f"abstract/{name}.png"


def _draw_arrow(draw: ImageDraw.ImageDraw, center: tuple[int, int], length: int, angle_degrees: float, color) -> None:
    cx, cy = center
    rad = math.radians(angle_degrees)
    tip = (cx + length * math.cos(rad), cy - length * math.sin(rad))
    tail = (cx - length * math.cos(rad), cy + length * math.sin(rad))
    draw.line([tail, tip], fill=color, width=8)
    head_len = length * 0.35
    for offset in (35, -35):
        wing_rad = math.radians(angle_degrees + 180 + offset)
        wing = (tip[0] + head_len * math.cos(wing_rad), tip[1] - head_len * math.sin(wing_rad))
        draw.line([tip, wing], fill=color, width=8)


def rotation_question(name: str, start_angle: float, step: float) -> dict:
    """Sequence: an arrow rotates by a constant step each panel. Answer = the next rotation."""
    image, draw = _new_canvas()
    panel_w = CANVAS // 4
    angles = [start_angle, start_angle + step, start_angle + 2 * step]
    for i, angle in enumerate(angles):
        cx = panel_w // 2 + i * panel_w
        draw.rectangle([i * panel_w, 0, (i + 1) * panel_w, CANVAS], outline=MUTED, width=1)
        _draw_arrow(draw, (cx, CANVAS // 2), 60, angle, ACCENT)
    draw.rectangle([3 * panel_w, 0, CANVAS, CANVAS], outline=MUTED, width=1)
    draw.text((3 * panel_w + panel_w // 2 - 10, CANVAS // 2 - 15), "?", fill=INK)
    question_url = _save(image, f"{name}-question")

    correct_angle = start_angle + 3 * step
    option_angles = [correct_angle, start_angle, start_angle + step, correct_angle + step]
    option_urls = []
    for i, angle in enumerate(option_angles):
        opt_img, opt_draw = _new_canvas()
        _draw_arrow(opt_draw, (CANVAS // 2, CANVAS // 2), 90, angle, ACCENT)
        option_urls.append(_save(opt_img, f"{name}-option-{i}"))

    return {
        "question_image_url": question_url,
        "question_image_alt_text": "A sequence of three rotating arrows, followed by a question mark panel.",
        "options": [(option_urls[i], "A rotated arrow.", i == 0) for i in range(4)],
    }


def sequence_count_question(name: str, start: int, step: int) -> dict:
    """Sequence: the number of filled squares increases by a constant step. Answer = the count
    that continues the pattern."""
    image, draw = _new_canvas()
    panel_w = CANVAS // 4
    counts = [start, start + step, start + 2 * step]
    for i, count in enumerate(counts):
        draw.rectangle([i * panel_w, 0, (i + 1) * panel_w, CANVAS], outline=MUTED, width=1)
        _draw_square_row(draw, i * panel_w, panel_w, count)
    draw.rectangle([3 * panel_w, 0, CANVAS, CANVAS], outline=MUTED, width=1)
    draw.text((3 * panel_w + panel_w // 2 - 10, CANVAS // 2 - 15), "?", fill=INK)
    question_url = _save(image, f"{name}-question")

    correct_count = start + 3 * step
    option_counts = [correct_count, correct_count - step, correct_count + step, start]
    option_urls = []
    for i, count in enumerate(option_counts):
        opt_img, opt_draw = _new_canvas()
        _draw_square_row(opt_draw, 0, CANVAS, max(count, 0))
        option_urls.append(_save(opt_img, f"{name}-option-{i}"))

    return {
        "question_image_url": question_url,
        "question_image_alt_text": "A sequence of panels with an increasing number of filled squares, followed by a question mark panel.",
        "options": [(option_urls[i], "A panel with filled squares.", i == 0) for i in range(4)],
    }


def _draw_square_row(draw: ImageDraw.ImageDraw, x_offset: int, width: int, count: int) -> None:
    if count <= 0:
        return
    size = 20
    gap = 6
    total_width = count * size + (count - 1) * gap
    start_x = x_offset + (width - total_width) // 2
    y = CANVAS // 2 - size // 2
    for i in range(count):
        x = start_x + i * (size + gap)
        draw.rectangle([x, y, x + size, y + size], fill=ACCENT)


def mirror_question(name: str, seed: int) -> dict:
    """An asymmetric shape and its horizontal mirror; the odd option out is the one that is NOT
    a true mirror."""
    image, draw = _new_canvas()
    _draw_l_shape(draw, CANVAS // 4, CANVAS // 2, mirrored=False, seed=seed)
    draw.line([(CANVAS // 2, 20), (CANVAS // 2, CANVAS - 20)], fill=MUTED, width=2)
    _draw_l_shape(draw, 3 * CANVAS // 4, CANVAS // 2, mirrored=True, seed=seed)
    question_url = _save(image, f"{name}-question")

    option_urls = []
    # Options: 0=correct mirror, 1=original (not mirrored), 2=rotated (not mirrored),
    # 3=mirrored+rotated (not a pure mirror).
    variants = [
        {"mirrored": True, "rotate": 0},
        {"mirrored": False, "rotate": 0},
        {"mirrored": False, "rotate": 90},
        {"mirrored": True, "rotate": 90},
    ]
    for i, variant in enumerate(variants):
        opt_img, opt_draw = _new_canvas()
        _draw_l_shape(opt_draw, CANVAS // 2, CANVAS // 2, mirrored=variant["mirrored"], seed=seed, rotate=variant["rotate"])
        option_urls.append(_save(opt_img, f"{name}-option-{i}"))

    return {
        "question_image_url": question_url,
        "question_image_alt_text": "An asymmetric shape on the left and its mirror image on the right, separated by a vertical line.",
        "options": [(option_urls[i], "A candidate mirror-image shape.", i == 0) for i in range(4)],
    }


def _draw_l_shape(draw: ImageDraw.ImageDraw, cx: int, cy: int, *, mirrored: bool, seed: int, rotate: int = 0) -> None:
    size = 50
    sign = -1 if mirrored else 1
    points = [
        (cx - size, cy - size), (cx, cy - size), (cx, cy),
        (cx + sign * size, cy), (cx + sign * size, cy + size // 2), (cx - size, cy + size // 2),
    ]
    if rotate:
        points = _rotate_points(points, (cx, cy), rotate)
    draw.polygon(points, fill=ACCENT, outline=INK)


def _rotate_points(points: list[tuple[float, float]], center: tuple[float, float], degrees: float) -> list[tuple[float, float]]:
    cx, cy = center
    rad = math.radians(degrees)
    result = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        result.append((cx + dx * math.cos(rad) - dy * math.sin(rad), cy + dx * math.sin(rad) + dy * math.cos(rad)))
    return result


_SHAPES = ["circle", "square", "triangle"]
_COLORS = [ACCENT, (25, 179, 107), (232, 77, 91), (245, 166, 35)]  # blue/success/danger/warning


def _draw_shape(draw: ImageDraw.ImageDraw, cx: int, cy: int, shape: str, color, size: int = 50) -> None:
    if shape == "circle":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=color)
    elif shape == "square":
        draw.rectangle([cx - size, cy - size, cx + size, cy + size], fill=color)
    else:
        draw.polygon([(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)], fill=color)


def odd_one_out_question(name: str, shared_shape: str, odd_shape: str, color) -> dict:
    """Four options: three share a shape, one has a different shape (same color/size) — the
    'odd one out' by shape, not color, so the difference is unambiguous."""
    image, draw = _new_canvas()
    draw.text((20, CANVAS // 2 - 10), "Which one does not belong?", fill=INK)
    question_url = _save(image, f"{name}-question")

    shapes = [shared_shape, shared_shape, shared_shape, odd_shape]
    option_urls = []
    for i, shape in enumerate(shapes):
        opt_img, opt_draw = _new_canvas()
        _draw_shape(opt_draw, CANVAS // 2, CANVAS // 2, shape, color)
        option_urls.append(_save(opt_img, f"{name}-option-{i}"))

    return {
        "question_image_url": question_url,
        "question_image_alt_text": "Four shapes; three share a common form and one is different.",
        "options": [(option_urls[i], f"A {shapes[i]} shape.", i == 3) for i in range(4)],
    }


def matrix_question(name: str, seed: int) -> dict:
    """A 3x3 checkerboard-style grid with the bottom-right cell blank. Answer = the cell that
    continues the alternating pattern."""
    image, draw = _new_canvas()
    cell = CANVAS // 3
    for row in range(3):
        for col in range(3):
            x0, y0 = col * cell, row * cell
            x1, y1 = x0 + cell, y0 + cell
            draw.rectangle([x0, y0, x1, y1], outline=MUTED, width=1)
            if row == 2 and col == 2:
                draw.text((x0 + cell // 2 - 8, y0 + cell // 2 - 10), "?", fill=INK)
                continue
            filled = (row + col) % 2 == 0
            if filled:
                draw.rectangle([x0 + 10, y0 + 10, x1 - 10, y1 - 10], fill=INK)
    question_url = _save(image, f"{name}-question")

    # (row=2, col=2): (2+2)%2==0 -> filled is correct.
    option_urls = []
    variants = [True, False, True, False]  # correct is index 0 (filled); include a decoy at 2
    for i, filled in enumerate(variants):
        opt_img, opt_draw = _new_canvas()
        if filled:
            opt_draw.rectangle([CANVAS // 2 - 40, CANVAS // 2 - 40, CANVAS // 2 + 40, CANVAS // 2 + 40], fill=INK)
        option_urls.append(_save(opt_img, f"{name}-option-{i}"))

    return {
        "question_image_url": question_url,
        "question_image_alt_text": "A 3x3 grid of alternating filled and empty cells with the bottom-right cell missing.",
        "options": [(option_urls[i], "A candidate grid cell.", i == 0) for i in range(4)],
    }


def generate_all() -> list[dict]:
    questions: list[dict] = []

    for i, (start, step) in enumerate([(0, 45), (15, 30), (90, -45), (0, 90), (10, 60), (200, 40)]):
        questions.append({**rotation_question(f"rotation-{i}", start, step), "topic": "rotation", "difficulty": "MEDIUM"})

    for i, (start, step) in enumerate([(1, 1), (2, 2), (1, 2), (3, 1), (2, 3), (1, 3)]):
        questions.append({**sequence_count_question(f"sequence-{i}", start, step), "topic": "shape-sequences", "difficulty": "EASY"})

    for i in range(6):
        questions.append({**mirror_question(f"mirror-{i}", seed=i), "topic": "mirroring", "difficulty": "HARD"})

    combos = [
        ("circle", "square"), ("square", "triangle"), ("triangle", "circle"),
        ("circle", "triangle"), ("square", "circle"), ("triangle", "square"),
    ]
    for i, (shared, odd) in enumerate(combos):
        color = _COLORS[i % len(_COLORS)]
        questions.append({**odd_one_out_question(f"odd-one-out-{i}", shared, odd, color), "topic": "odd-one-out", "difficulty": "EASY"})

    for i in range(6):
        questions.append({**matrix_question(f"matrix-{i}", seed=i), "topic": "abstract-matrices", "difficulty": "MEDIUM"})

    return questions


if __name__ == "__main__":
    generated = generate_all()
    print(f"Generated {len(generated)} abstract-reasoning image questions into {_output_dir()}")
