"""Регенерація іконок погоди з набору Meteocons (Bas Milius, MIT).

Запускати ВРУЧНУ під час розробки, коли треба оновити чи додати іконки.
У рантаймі НЕ використовується — бот вантажить готові assets/icons/*.png (Pillow),
тож resvg-py у продакшені не потрібен.

Потрібно (тільки для запуску цього скрипта):
    pip install resvg-py

Джерело: @meteocons/svg-static (npm, стиль fill) через jsDelivr CDN.
"""

import io
import os
import urllib.error
import urllib.request

import resvg_py
from PIL import Image

BASE = "https://cdn.jsdelivr.net/npm/@meteocons/svg-static@0.1.0/fill/"

# Наш ключ іконки (weather/codes.py) -> кандидати імен файлів Meteocons.
# Беремо перший варіант, що завантажився (на випадок іншого імені).
ICONS = {
    "clear":         ["clear-day"],
    "partly-cloudy": ["partly-cloudy-day"],
    "overcast":      ["overcast", "cloudy", "overcast-day"],
    "fog":           ["fog", "fog-day"],
    "drizzle":       ["drizzle"],
    "sleet":         ["sleet"],
    "rain":          ["rain"],
    "showers":       ["partly-cloudy-day-rain", "rain"],
    "snow":          ["snow"],
    "thunderstorms": ["thunderstorms", "thunderstorms-day"],
}

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
os.makedirs(OUT, exist_ok=True)


def _fetch_svg(name: str) -> str | None:
    try:
        with urllib.request.urlopen(BASE + name + ".svg", timeout=30) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError:
        return None


for key, candidates in ICONS.items():
    svg = used = None
    for name in candidates:
        svg = _fetch_svg(name)
        if svg is not None:
            used = name
            break
    if svg is None:
        print(f"  ⚠ {key}: жоден кандидат не знайдено ({candidates})")
        continue

    raw = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=512, height=512))
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    else:
        img = Image.frombytes("RGBA", (512, 512), raw)
    img.save(os.path.join(OUT, f"{key}.png"))
    print(f"  {used}.svg -> assets/icons/{key}.png")

print("OK")
