"""WMO weather_code → (український опис, ключ іконки).

Коди — це стандарт WMO 4677, який повертає Open-Meteo у полі `weather_code`.
Ключі іконок збігаються з файлами assets/icons/<key>.png та fallback-примітивами
у render/icons.py: clear, partly-cloudy, overcast, fog, drizzle, sleet, rain,
showers, snow, thunderstorms.
"""

# Ключі іконок (файл assets/icons/<key>.png)
ICON_CLEAR = "clear"            # ясно
ICON_PARTLY = "partly-cloudy"   # мінлива хмарність
ICON_OVERCAST = "overcast"      # похмуро
ICON_FOG = "fog"                # туман
ICON_DRIZZLE = "drizzle"        # мряка
ICON_SLEET = "sleet"            # крижаний дощ / мокрий сніг
ICON_RAIN = "rain"              # дощ
ICON_SHOWERS = "showers"        # зливи
ICON_SNOW = "snow"              # сніг
ICON_STORM = "thunderstorms"    # гроза

_FALLBACK = ("Невідомо", ICON_OVERCAST)

# code → (опис, іконка)
_TABLE: dict[int, tuple[str, str]] = {
    0:  ("Ясно", ICON_CLEAR),
    1:  ("Переважно ясно", ICON_PARTLY),
    2:  ("Мінлива хмарність", ICON_PARTLY),
    3:  ("Похмуро", ICON_OVERCAST),
    45: ("Туман", ICON_FOG),
    48: ("Туман з памороззю", ICON_FOG),
    51: ("Слабка мряка", ICON_DRIZZLE),
    53: ("Мряка", ICON_DRIZZLE),
    55: ("Сильна мряка", ICON_DRIZZLE),
    56: ("Крижана мряка", ICON_SLEET),
    57: ("Сильна крижана мряка", ICON_SLEET),
    61: ("Невеликий дощ", ICON_RAIN),
    63: ("Дощ", ICON_RAIN),
    65: ("Сильний дощ", ICON_RAIN),
    66: ("Крижаний дощ", ICON_SLEET),
    67: ("Сильний крижаний дощ", ICON_SLEET),
    71: ("Невеликий сніг", ICON_SNOW),
    73: ("Сніг", ICON_SNOW),
    75: ("Сильний сніг", ICON_SNOW),
    77: ("Сніжна крупа", ICON_SNOW),
    80: ("Невеликі зливи", ICON_SHOWERS),
    81: ("Зливи", ICON_SHOWERS),
    82: ("Сильні зливи", ICON_SHOWERS),
    85: ("Снігопад", ICON_SNOW),
    86: ("Сильний снігопад", ICON_SNOW),
    95: ("Гроза", ICON_STORM),
    96: ("Гроза з градом", ICON_STORM),
    99: ("Сильна гроза з градом", ICON_STORM),
}


def describe(code: int | None) -> tuple[str, str]:
    """Повертає (опис, ключ іконки) для WMO-коду."""
    if code is None:
        return _FALLBACK
    return _TABLE.get(int(code), _FALLBACK)
