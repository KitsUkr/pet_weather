"""Поєднує отримання погоди й рендер картки — спільна логіка для хендлерів
і планувальника розсилки.
"""

import asyncio

import texts
from render.card import render_weather_card
from weather.client import get_forecast
from weather.codes import describe
from weather.summary import summarize_today


async def build_weather_photo(city: str, lat: float, lon: float) -> tuple[bytes, str]:
    """Повертає (PNG-байти картки, HTML-підпис) для заданих координат.

    Кидає weather.client.WeatherError, якщо погоду не вдалося отримати.
    """
    forecast = await get_forecast(lat, lon)
    current = forecast["current"]
    days = forecast["days"]
    hours = forecast.get("hours", [])

    # Рендер у Pillow — CPU-bound, виносимо в окремий потік, щоб не блокувати loop.
    png = await asyncio.to_thread(render_weather_card, city, current, days, hours)

    desc = describe(current.get("code"))[0]
    caption = texts.WEATHER_CAPTION.format(
        city=city, desc=desc, temp=_fmt_temp(current.get("temp"))
    )
    caption = f"{caption}\n\n{summarize_today(current, days, hours)}"
    return png, caption


def _fmt_temp(value) -> str:
    if value is None:
        return "—"
    value = int(round(value))
    return f"+{value}°" if value > 0 else f"{value}°"
