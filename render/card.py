"""Рендер картки прогнозу погоди у PNG (Pillow).

Головна функція: render_weather_card(city, current, days, hours) -> bytes (PNG).
`current`, `days`, `hours` мають формат, який повертає weather.client.get_forecast.

Макет — горизонтальний: зліва поточна погода (великим планом), справа —
погодинний прогноз тільки на сьогодні (з кроком 1 година) на плоскій
напівпрозорій панелі у стилі віджета MIUI.
"""

import datetime as dt
import io

from PIL import Image, ImageDraw, ImageFilter

from render import icons
from render.fonts import load_font
from weather.codes import describe

WIDTH, HEIGHT = 900, 470

_TEXT = (255, 255, 255)
_TEXT_DIM = (231, 239, 250)
# Панель погодинного прогнозу — у стилі віджета MIUI: плоска напівпрозора
# заливка (трохи приглушує фон), світлий текст, ледь помітна рамка.
_PANEL_FILL = (74, 92, 134, 112)    # приглушена напівпрозора заливка
_PANEL_EDGE = (255, 255, 255, 46)   # тонка світла рамка
_PANEL_TEXT = (246, 249, 255)       # світлий основний текст
_PANEL_TEXT_DIM = (208, 218, 238)   # світлий приглушений текст
_PANEL_RADIUS = 28

# Скільки годин показуємо та з яким кроком (год.). Беремо лише сьогоднішні
# години, тож у вечірні години рядків буде менше.
_HOURS_COUNT = 8
_HOURS_STEP = 1

# Градієнт фону (верх, низ) залежно від типу погоди — світлий, «небесний».
# Ключі збігаються з weather/codes.py.
_GRADIENTS = {
    "clear":         ((86, 156, 240), (156, 204, 250)),   # ясне небо
    "partly-cloudy": ((104, 158, 214), (164, 198, 234)),  # мінлива хмарність
    "overcast":      ((120, 138, 166), (180, 196, 218)),  # похмуро, сіріше
    "fog":           ((140, 152, 168), (196, 204, 216)),  # туман
    "drizzle":       ((104, 134, 172), (158, 184, 212)),  # мряка
    "sleet":         ((100, 124, 160), (152, 178, 206)),  # крижаний дощ
    "rain":          ((84, 116, 158), (140, 168, 200)),   # дощ
    "showers":       ((92, 128, 168), (148, 178, 208)),   # зливи
    "snow":          ((140, 168, 204), (206, 222, 240)),  # сніг
    "thunderstorms": ((74, 82, 116), (128, 136, 172)),    # гроза
}
_GRADIENT_DEFAULT = ((96, 150, 212), (158, 196, 236))

_UK_MONTHS = [
    "", "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]
_UK_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def render_weather_card(
    city: str,
    current: dict,
    days: list[dict],
    hours: list[dict] | None = None,
) -> bytes:
    icon_key = describe(current.get("code"))[1]
    desc = describe(current.get("code"))[0]

    img = _gradient_bg(icon_key)
    _add_clouds(img)
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_current(img, draw, city, days, current, desc, icon_key)
    _draw_hourly(img, draw, current, hours or [])

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# ── Ліва частина: поточна погода ────────────────────────────────────────────────

def _draw_current(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    city: str,
    days: list[dict],
    current: dict,
    desc: str,
    icon_key: str,
) -> None:
    f_city = load_font(44)
    f_date = load_font(24)
    f_temp = load_font(104)
    f_desc = load_font(30)
    f_meta = load_font(24)

    # Місто + дата
    draw.text((44, 32), city, font=f_city, fill=_TEXT)
    draw.text((46, 88), _date_label(days), font=f_date, fill=_TEXT_DIM)

    # Велика іконка + температура
    icon = icons.render(icon_key, 150)
    img.paste(icon, (40, 132), icon)
    draw.text((204, 140), _deg(current.get("temp")), font=f_temp, fill=_TEXT)

    # Опис + макс/мін за сьогодні
    draw.text((210, 256), desc, font=f_desc, fill=_TEXT_DIM)
    draw.text((210, 296), _hi_lo(days), font=f_meta, fill=_TEXT_DIM)

    # Метрики
    meta_lines = [
        f"Відчувається {_deg(current.get('feels'))}",
        f"Вітер  {_fmt_num(current.get('wind'))} м/с",
        f"Вологість  {_fmt_num(current.get('humidity'))}%",
    ]
    y = 348
    for line in meta_lines:
        draw.text((44, y), line, font=f_meta, fill=_TEXT_DIM)
        y += 36


# ── Права частина: погодинний прогноз ──────────────────────────────────────────

def _draw_hourly(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    current: dict,
    hours: list[dict],
) -> None:
    x0, y0, x1, y1 = 478, 36, WIDTH - 36, HEIGHT - 36
    _flat_panel(img, (x0, y0, x1, y1), _PANEL_RADIUS)

    f_head = load_font(24)
    f_time = load_font(24)
    f_temp = load_font(24)

    head_h = 48
    draw.text((x0 + 26, y0 + head_h / 2 + 2), "Погодинний прогноз",
              font=f_head, fill=_PANEL_TEXT_DIM, anchor="lm")

    rows = _select_hours(hours, current.get("time"))
    if not rows:
        return

    icon_size = 34
    icon_cx = x0 + 34
    time_x = x0 + 70
    temp_x = x1 - 26

    area_top = y0 + head_h
    row_h = (y1 - area_top) / len(rows)
    for i, hour in enumerate(rows):
        cy = area_top + row_h * (i + 0.5)

        icon = icons.render(describe(hour.get("code"))[1], icon_size)
        img.paste(icon, (int(icon_cx - icon_size / 2), int(cy - icon_size / 2)), icon)

        draw.text((time_x, cy), _hour_label(hour["time"]),
                  font=f_time, fill=_PANEL_TEXT, anchor="lm")

        draw.text((temp_x, cy), _deg(hour.get("temp")),
                  font=f_temp, fill=_PANEL_TEXT, anchor="rm")


def _select_hours(hours: list[dict], current_time: str | None) -> list[dict]:
    """Години від поточної до кінця сьогоднішнього дня (без переходу на завтра).

    Крок — _HOURS_STEP год., максимум _HOURS_COUNT рядків. Якщо час невідомий,
    показуємо найближчі години без обмеження днем.
    """
    if not hours:
        return []

    now = _parse_dt(current_time)
    now_floor = now.replace(minute=0, second=0, microsecond=0) if now else None
    today = now.date() if now else None

    todays = []
    for hour in hours:
        t = _parse_dt(hour.get("time"))
        if t is None:
            continue
        if now_floor is not None and t < now_floor:
            continue
        if today is not None and t.date() != today:
            break  # почалося завтра — зупиняємось
        todays.append(hour)

    if not todays:  # час невідомий — відкат на найближчі години
        todays = hours

    return todays[::_HOURS_STEP][:_HOURS_COUNT]


# ── Фон ─────────────────────────────────────────────────────────────────────────

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


def _flat_panel(img: Image.Image, box: tuple[int, int, int, int], radius: int) -> None:
    """Малює плоску напівпрозору панель у стилі віджета погоди MIUI.

    Без розмиття й бліків: спокійна напівпрозора заливка, що трохи приглушує
    фон, тонка світла рамка та дуже м'яка тінь під панеллю.
    """
    x0, y0, x1, y1 = box

    # Дуже м'яка тінь під панеллю
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x0, y0 + 6, x1, y1 + 8], radius=radius, fill=(28, 44, 72, 55)
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))

    # Плоска напівпрозора заливка + тонка рамка
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=_PANEL_FILL)
    odraw.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=_PANEL_EDGE, width=1)
    img.alpha_composite(overlay)


def _add_clouds(img: Image.Image) -> None:
    """М'які білі «хмари» вгорі — для повітряного вигляду як у застосунку."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    blobs = [
        (-80, -60, 320, 180),
        (160, -90, 540, 150),
        (WIDTH - 360, -50, WIDTH + 100, 200),
    ]
    for box in blobs:
        d.ellipse(box, fill=(255, 255, 255, 64))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(46)))


# ── Утиліти ───────────────────────────────────────────────────────────────────

def _date_label(days: list[dict]) -> str:
    date = _parse_date(days[0]["date"]) if days else dt.date.today()
    if date is None:
        date = dt.date.today()
    return f"{date.day} {_UK_MONTHS[date.month]}"


def _hi_lo(days: list[dict]) -> str:
    if not days:
        return ""
    today = days[0]
    return f"{_deg(today.get('tmax'))} / {_deg(today.get('tmin'))}"


def _hour_label(time_str: str | None) -> str:
    t = _parse_dt(time_str)
    if t is None:
        return "—"
    return t.strftime("%H:%M")


def _parse_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _deg(value) -> str:
    if value is None:
        return "—"
    return f"{int(round(value))}°"


def _fmt_num(value) -> str:
    if value is None:
        return "—"
    return str(int(round(value)))
