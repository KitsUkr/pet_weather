"""Рендер картки прогнозу погоди у PNG (Pillow).

Головна функція: render_weather_card(city, current, days) -> bytes (PNG).
`current` і `days` мають формат, який повертає weather.client.get_forecast.
"""

import datetime as dt
import io

from PIL import Image, ImageDraw

from render import icons
from render.fonts import load_font
from weather.codes import describe

WIDTH, HEIGHT = 820, 520

_TEXT = (255, 255, 255)
_TEXT_DIM = (228, 236, 248)
_PANEL = (255, 255, 255, 38)  # напівпрозора нижня панель
_PANEL_TEXT = (58, 78, 108)        # темний текст на світлій панелі
_PANEL_TEXT_DIM = (96, 116, 146)

# Градієнт фону (верх, низ) залежно від типу погоди.
_GRADIENTS = {
    "sun":   ((58, 141, 245), (137, 196, 255)),
    "cloud": ((96, 125, 160), (158, 184, 214)),
    "fog":   ((120, 132, 148), (178, 188, 200)),
    "rain":  ((68, 96, 138), (110, 140, 178)),
    "snow":  ((120, 150, 188), (196, 214, 236)),
    "storm": ((58, 64, 96), (104, 112, 150)),
}
_GRADIENT_DEFAULT = ((90, 120, 160), (150, 180, 210))

_UK_MONTHS = [
    "", "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]
_UK_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def render_weather_card(city: str, current: dict, days: list[dict]) -> bytes:
    icon_key = describe(current.get("code"))[1]
    desc = describe(current.get("code"))[0]

    img = _gradient_bg(icon_key)
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_header(draw, city, days)
    _draw_current(img, draw, current, desc, icon_key)
    _draw_forecast_row(img, draw, days)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# ── Секції ────────────────────────────────────────────────────────────────────

def _draw_header(draw: ImageDraw.ImageDraw, city: str, days: list[dict]) -> None:
    f_city = load_font(46)
    f_date = load_font(26)

    draw.text((44, 36), city, font=f_city, fill=_TEXT)
    draw.text((46, 96), _date_label(days), font=f_date, fill=_TEXT_DIM)


def _draw_current(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    current: dict,
    desc: str,
    icon_key: str,
) -> None:
    # Велика іконка зліва
    icon = icons.render(icon_key, 200)
    img.paste(icon, (40, 150), icon)

    # Температура справа від іконки
    f_temp = load_font(96)
    f_desc = load_font(30)
    f_meta = load_font(26)

    temp = _fmt_temp(current.get("temp"))
    draw.text((270, 168), temp, font=f_temp, fill=_TEXT)
    draw.text((276, 286), desc, font=f_desc, fill=_TEXT_DIM)

    meta_lines = [
        f"Відчувається як {_fmt_temp(current.get('feels'))}",
        f"Вітер  {_fmt_num(current.get('wind'))} м/с",
        f"Вологість  {_fmt_num(current.get('humidity'))}%",
    ]
    y = 168
    for line in meta_lines:
        draw.text((560, y), line, font=f_meta, fill=_TEXT_DIM)
        y += 40


def _draw_forecast_row(
    img: Image.Image, draw: ImageDraw.ImageDraw, days: list[dict]
) -> None:
    # Нижня напівпрозора панель
    panel_top = 360
    icon_size = 58
    draw.rounded_rectangle(
        [24, panel_top, WIDTH - 24, HEIGHT - 24], radius=22, fill=_PANEL
    )

    # Перший день — «сьогодні»; у рядку показуємо наступні дні.
    upcoming = days[1:5] if len(days) > 1 else days[:4]
    if not upcoming:
        return

    f_day = load_font(24)
    f_temp = load_font(24)

    n = len(upcoming)
    col_w = (WIDTH - 48) / n
    for i, day in enumerate(upcoming):
        center_x = int(48 + col_w * i + col_w / 2)

        draw.text((center_x, panel_top + 24), _weekday(day["date"]),
                  font=f_day, fill=_PANEL_TEXT, anchor="mm")

        icon = icons.render(describe(day.get("code"))[1], icon_size)
        img.paste(icon, (center_x - icon_size // 2, panel_top + 42), icon)

        tmax = _fmt_temp(day.get("tmax"))
        tmin = _fmt_temp(day.get("tmin"))
        draw.text((center_x, panel_top + 116), f"{tmax} / {tmin}",
                  font=f_temp, fill=_PANEL_TEXT_DIM, anchor="mm")


# ── Утиліти ───────────────────────────────────────────────────────────────────

def _gradient_bg(icon_key: str) -> Image.Image:
    top, bottom = _GRADIENTS.get(icon_key, _GRADIENT_DEFAULT)
    base = Image.new("RGB", (WIDTH, HEIGHT), top)
    grad = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        grad.putpixel((0, y), tuple(
            int(top[c] + (bottom[c] - top[c]) * t) for c in range(3)
        ))
    base.paste(grad.resize((WIDTH, HEIGHT)), (0, 0))
    return base.convert("RGBA")


def _date_label(days: list[dict]) -> str:
    date = _parse_date(days[0]["date"]) if days else dt.date.today()
    if date is None:
        date = dt.date.today()
    return f"{date.day} {_UK_MONTHS[date.month]}"


def _weekday(date_str: str) -> str:
    date = _parse_date(date_str)
    if date is None:
        return "—"
    return _UK_WEEKDAYS[date.weekday()]


def _parse_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _fmt_temp(value) -> str:
    if value is None:
        return "—"
    value = int(round(value))
    if value > 0:
        return f"+{value}°"
    return f"{value}°"


def _fmt_num(value) -> str:
    if value is None:
        return "—"
    return str(int(round(value)))
