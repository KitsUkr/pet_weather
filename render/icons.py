"""Іконки погоди: набір Meteocons (PNG) з відкатом на примітиви Pillow.

render(key, size) спершу пробує готову іконку Meteocons з assets/icons/<key>.png
(сконвертовані з SVG, ліцензія MIT). Якщо файлу немає — малюємо примітивами,
щоб бот працював навіть без ассетів. Ключі збігаються з weather/codes.py:
clear, partly-cloudy, overcast, fog, drizzle, sleet, rain, showers, snow,
thunderstorms.
"""

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

_ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

# Палітра
_SUN = (255, 193, 59)
_SUN_CORE = (255, 214, 102)
_CLOUD = (245, 248, 252)
_CLOUD_SHADOW = (208, 217, 230)
_RAIN = (74, 144, 226)
_SNOW = (224, 240, 255)
_FOG = (200, 208, 220)
_BOLT = (255, 209, 71)


def render(key: str, size: int) -> Image.Image:
    """Повертає RGBA-іконку погоди за ключем (Meteocons або примітив)."""
    icon = _load_icon(key)
    if icon is not None:
        return icon.resize((size, size), Image.LANCZOS)

    # Відкат: малюємо примітивами, якщо PNG-ассета немає.
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _DRAWERS.get(key, _draw_cloud_only)(draw, size)
    return img


@lru_cache(maxsize=16)
def _load_icon(key: str) -> Image.Image | None:
    """Завантажує Meteocons-іконку assets/icons/<key>.png (None, якщо нема)."""
    path = _ICONS_DIR / f"{key}.png"
    if not path.is_file():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


# ── Примітиви ─────────────────────────────────────────────────────────────────

def _draw_sun(draw: ImageDraw.ImageDraw, size: int, cx=None, cy=None, r=None) -> None:
    cx = size * 0.5 if cx is None else cx
    cy = size * 0.5 if cy is None else cy
    r = size * 0.24 if r is None else r

    # Промені
    ray_len = r * 0.7
    for i in range(8):
        ang = math.pi * i / 4
        x1 = cx + math.cos(ang) * (r + r * 0.25)
        y1 = cy + math.sin(ang) * (r + r * 0.25)
        x2 = cx + math.cos(ang) * (r + r * 0.25 + ray_len)
        y2 = cy + math.sin(ang) * (r + r * 0.25 + ray_len)
        draw.line([(x1, y1), (x2, y2)], fill=_SUN, width=max(2, int(size * 0.03)))

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_SUN)
    draw.ellipse(
        [cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=_SUN_CORE
    )


def _cloud_box(draw: ImageDraw.ImageDraw, size: int, fill, dy: float = 0.0) -> None:
    """Малює хмару у нижній частині квадрата."""
    w = size
    base_y = size * (0.62 + dy)
    # Тінь знизу
    draw.rounded_rectangle(
        [w * 0.18, base_y - w * 0.16, w * 0.86, base_y + w * 0.04],
        radius=w * 0.1, fill=fill,
    )
    # Три «горбики»
    draw.ellipse([w * 0.16, base_y - w * 0.22, w * 0.46, base_y + w * 0.08], fill=fill)
    draw.ellipse([w * 0.34, base_y - w * 0.34, w * 0.70, base_y + w * 0.04], fill=fill)
    draw.ellipse([w * 0.54, base_y - w * 0.24, w * 0.86, base_y + w * 0.06], fill=fill)


def _draw_cloud_only(draw: ImageDraw.ImageDraw, size: int) -> None:
    # Невеличке сонце за хмарою для «мінливої хмарності»
    _draw_sun(draw, size, cx=size * 0.62, cy=size * 0.36, r=size * 0.16)
    _cloud_box(draw, size, _CLOUD_SHADOW, dy=0.02)
    _cloud_box(draw, size, _CLOUD)


def _draw_cloud_plain(draw: ImageDraw.ImageDraw, size: int) -> None:
    _cloud_box(draw, size, _CLOUD_SHADOW, dy=0.02)
    _cloud_box(draw, size, _CLOUD)


def _draw_fog(draw: ImageDraw.ImageDraw, size: int) -> None:
    _cloud_box(draw, size, _CLOUD)
    w = size
    width = max(2, int(size * 0.035))
    for i in range(3):
        y = size * (0.74 + i * 0.08)
        x0 = w * (0.2 + (i % 2) * 0.06)
        x1 = w * (0.82 - (i % 2) * 0.06)
        draw.line([(x0, y), (x1, y)], fill=_FOG, width=width)


def _draw_rain(draw: ImageDraw.ImageDraw, size: int) -> None:
    _draw_cloud_plain(draw, size)
    w = size
    width = max(2, int(size * 0.035))
    for i in range(3):
        x = w * (0.32 + i * 0.18)
        y0 = size * 0.76
        draw.line([(x, y0), (x - w * 0.04, y0 + w * 0.14)], fill=_RAIN, width=width)


def _draw_snow(draw: ImageDraw.ImageDraw, size: int) -> None:
    _draw_cloud_plain(draw, size)
    w = size
    r = w * 0.03
    for i in range(3):
        cx = w * (0.32 + i * 0.18)
        cy = size * 0.82
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_SNOW)


def _draw_storm(draw: ImageDraw.ImageDraw, size: int) -> None:
    _draw_cloud_plain(draw, size)
    w = size
    bolt = [
        (w * 0.50, w * 0.66),
        (w * 0.40, w * 0.84),
        (w * 0.49, w * 0.84),
        (w * 0.42, w * 0.98),
        (w * 0.60, w * 0.78),
        (w * 0.50, w * 0.78),
        (w * 0.56, w * 0.66),
    ]
    draw.polygon(bolt, fill=_BOLT)


# Fallback-примітиви для всіх ключів codes.py (на випадок відсутнього PNG).
_DRAWERS = {
    "clear": _draw_sun,
    "partly-cloudy": _draw_cloud_only,
    "overcast": _draw_cloud_plain,
    "fog": _draw_fog,
    "drizzle": _draw_rain,
    "sleet": _draw_rain,
    "rain": _draw_rain,
    "showers": _draw_rain,
    "snow": _draw_snow,
    "thunderstorms": _draw_storm,
}
