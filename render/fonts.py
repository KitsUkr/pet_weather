"""Пошук .ttf-шрифту з підтримкою кирилиці (з fallback-ланцюжком).

Порядок пошуку:
  1. FONT_PATH з .env (якщо задано);
  2. будь-який .ttf у assets/fonts/ (bundled);
  3. DejaVuSans — є в Docker (пакет fonts-dejavu-core) і у багатьох Linux;
  4. Arial / Segoe UI — типові Windows-шрифти (для локальної розробки);
  5. ImageFont.load_default() — останній рятунок (без кирилиці, але не падає).

Знайдений шлях кешується. Якщо не знайдено жодного .ttf — load_default().
"""

import logging
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from config import FONT_PATH

logger = logging.getLogger(__name__)

_ASSETS_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Кандидати на системні шрифти з кирилицею.
_SYSTEM_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",            # Pillow інколи знаходить за іменем
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "arial.ttf",
]


@lru_cache(maxsize=1)
def _resolve_font_file() -> str | None:
    # 1. Явний шлях з конфігу
    if FONT_PATH and Path(FONT_PATH).is_file():
        return FONT_PATH

    # 2. Bundled у assets/fonts/
    if _ASSETS_FONTS.is_dir():
        for ttf in sorted(_ASSETS_FONTS.glob("*.ttf")):
            return str(ttf)

    # 3-4. Системні кандидати
    for candidate in _SYSTEM_CANDIDATES:
        try:
            ImageFont.truetype(candidate, 12)
            return candidate
        except OSError:
            continue

    logger.warning(
        "Не знайдено .ttf-шрифту з кирилицею — використовується load_default(). "
        "Кирилиця може відображатися некоректно. Задайте FONT_PATH у .env."
    )
    return None


@lru_cache(maxsize=32)
def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Повертає шрифт заданого розміру (з кешуванням)."""
    path = _resolve_font_file()
    if path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()
