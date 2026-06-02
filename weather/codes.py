"""WMO weather_code → (український опис, ключ іконки).

Коди — це стандарт WMO 4677, який повертає Open-Meteo у полях
`weather_code`. Ключі іконок збігаються з тими, що вміє малювати
`render/icons.py`: sun, cloud, fog, rain, snow, storm.
"""

# Ключі іконок, які підтримує render/icons.py
ICON_SUN = "sun"
ICON_CLOUD = "cloud"
ICON_FOG = "fog"
ICON_RAIN = "rain"
ICON_SNOW = "snow"
ICON_STORM = "storm"

_FALLBACK = ("Невідомо", ICON_CLOUD)

# code → (опис, іконка)
_TABLE: dict[int, tuple[str, str]] = {
    0: ("Ясно", ICON_SUN),
    1: ("Переважно ясно", ICON_SUN),
    2: ("Мінлива хмарність", ICON_CLOUD),
    3: ("Похмуро", ICON_CLOUD),
    45: ("Туман", ICON_FOG),
    48: ("Паморозь", ICON_FOG),
    51: ("Слабка мряка", ICON_RAIN),
    53: ("Мряка", ICON_RAIN),
    55: ("Сильна мряка", ICON_RAIN),
    56: ("Крижана мряка", ICON_RAIN),
    57: ("Сильна крижана мряка", ICON_RAIN),
    61: ("Невеликий дощ", ICON_RAIN),
    63: ("Дощ", ICON_RAIN),
    65: ("Сильний дощ", ICON_RAIN),
    66: ("Крижаний дощ", ICON_RAIN),
    67: ("Сильний крижаний дощ", ICON_RAIN),
    71: ("Невеликий сніг", ICON_SNOW),
    73: ("Сніг", ICON_SNOW),
    75: ("Сильний сніг", ICON_SNOW),
    77: ("Сніжна крупа", ICON_SNOW),
    80: ("Невеликі зливи", ICON_RAIN),
    81: ("Зливи", ICON_RAIN),
    82: ("Сильні зливи", ICON_RAIN),
    85: ("Снігопад", ICON_SNOW),
    86: ("Сильний снігопад", ICON_SNOW),
    95: ("Гроза", ICON_STORM),
    96: ("Гроза з градом", ICON_STORM),
    99: ("Сильна гроза з градом", ICON_STORM),
}


def describe(code: int | None) -> tuple[str, str]:
    """Повертає (український опис, ключ іконки) для WMO-коду."""
    if code is None:
        return _FALLBACK
    return _TABLE.get(int(code), _FALLBACK)
