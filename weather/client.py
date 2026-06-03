"""Клієнт Open-Meteo: геокодинг міст + прогноз погоди.

Open-Meteo безкоштовний і не потребує API-ключа. Використовуємо один спільний
aiohttp.ClientSession на весь час життя бота (створюється лениво).
"""

import logging

import aiohttp

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

FORECAST_DAYS = 5
_TIMEOUT = aiohttp.ClientTimeout(total=15)

_session: aiohttp.ClientSession | None = None


class WeatherError(Exception):
    """Помилка отримання даних від Open-Meteo (мережа / поганий статус)."""


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=_TIMEOUT)
    return _session


async def close() -> None:
    """Закриває спільну сесію (виклик при зупинці бота)."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def geocode_city(name: str) -> dict | None:
    """Шукає координати міста за назвою.

    Спершу шукаємо серед українських міст (country=UA), якщо нічого не
    знайдено — повторюємо пошук без обмеження країни (на випадок закордону).
    Повертає dict {name, lat, lon, country, admin1} або None.
    """
    name = (name or "").strip()
    if not name:
        return None

    result = await _geocode(name, country="UA")
    if result is None:
        result = await _geocode(name, country=None)
    return result


async def _geocode(name: str, country: str | None) -> dict | None:
    params = {"name": name, "count": "1", "language": "uk", "format": "json"}
    if country:
        params["countryCode"] = country

    session = await _get_session()
    try:
        async with session.get(GEOCODE_URL, params=params) as resp:
            if resp.status != 200:
                logger.warning("Geocoding HTTP %s для '%s'", resp.status, name)
                return None
            data = await resp.json()
    except Exception as exc:
        logger.warning("Geocoding впав для '%s': %s", name, exc)
        raise WeatherError(str(exc)) from exc

    results = data.get("results") or []
    if not results:
        return None

    top = results[0]
    return {
        "name": top.get("name") or name,
        "lat": top["latitude"],
        "lon": top["longitude"],
        "country": top.get("country_code") or "",
        "admin1": top.get("admin1") or "",
    }


async def get_forecast(lat: float, lon: float) -> dict:
    """Повертає нормалізований прогноз: поточна погода + дні + години.

    Структура:
        {
          "current": {temp, feels, humidity, wind, code, time},
          "days":  [{date "YYYY-MM-DD", code, tmax, tmin}, ...],
          "hours": [{time "YYYY-MM-DDTHH:MM", code, temp}, ...]
        }
    """
    params = {
        "latitude": f"{lat}",
        "longitude": f"{lon}",
        "current": (
            "temperature_2m,apparent_temperature,"
            "relative_humidity_2m,wind_speed_10m,weather_code"
        ),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "hourly": "weather_code,temperature_2m",
        "timezone": "Europe/Kyiv",
        "forecast_days": str(FORECAST_DAYS),
        "wind_speed_unit": "ms",
    }

    session = await _get_session()
    try:
        async with session.get(FORECAST_URL, params=params) as resp:
            if resp.status != 200:
                raise WeatherError(f"HTTP {resp.status}")
            data = await resp.json()
    except WeatherError:
        raise
    except Exception as exc:
        logger.warning("Forecast впав (%.4f,%.4f): %s", lat, lon, exc)
        raise WeatherError(str(exc)) from exc

    return _normalize(data)


def _normalize(data: dict) -> dict:
    cur = data.get("current") or {}
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}

    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []

    days = []
    for i, date in enumerate(dates):
        days.append({
            "date": date,
            "code": _safe_int(codes[i]) if i < len(codes) else None,
            "tmax": _safe_round(tmax[i]) if i < len(tmax) else None,
            "tmin": _safe_round(tmin[i]) if i < len(tmin) else None,
        })

    htimes = hourly.get("time") or []
    hcodes = hourly.get("weather_code") or []
    htemps = hourly.get("temperature_2m") or []

    hours = []
    for i, time in enumerate(htimes):
        hours.append({
            "time": time,
            "code": _safe_int(hcodes[i]) if i < len(hcodes) else None,
            "temp": _safe_round(htemps[i]) if i < len(htemps) else None,
        })

    return {
        "current": {
            "temp": _safe_round(cur.get("temperature_2m")),
            "feels": _safe_round(cur.get("apparent_temperature")),
            "humidity": _safe_int(cur.get("relative_humidity_2m")),
            "wind": _safe_round(cur.get("wind_speed_10m")),
            "code": _safe_int(cur.get("weather_code")),
            "time": cur.get("time"),
        },
        "days": days,
        "hours": hours,
    }


def _safe_round(value) -> int | None:
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
