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
import urllib.request

import resvg_py
from PIL import Image

BASE = "https://cdn.jsdelivr.net/npm/@meteocons/svg-static@0.1.0/fill/"

# Файл Meteocons -> наш ключ іконки (див. weather/codes.py)
MAP = {
    "clear-day": "sun",
    "partly-cloudy-day": "cloud",
    "fog": "fog",
    "rain": "rain",
    "snow": "snow",
    "thunderstorms": "storm",
}

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
os.makedirs(OUT, exist_ok=True)

for src, key in MAP.items():
    svg = urllib.request.urlopen(BASE + src + ".svg", timeout=30).read().decode("utf-8")
    raw = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=512, height=512))
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    else:
        img = Image.frombytes("RGBA", (512, 512), raw)
    img.save(os.path.join(OUT, f"{key}.png"))
    print(f"  {src}.svg -> assets/icons/{key}.png")

print("OK")
