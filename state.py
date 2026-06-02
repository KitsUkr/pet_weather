"""Легкий in-memory стан: останнє показане користувачу місто.

Потрібно для кнопок «⭐ Зробити улюбленим» / «🔔 Підписатися»: callback_data
обмежений 64 байтами й не вміщує назву міста (кирилиця) + координати, тому
запам'ятовуємо останній показ у пам'яті процесу. Скидається при рестарті —
це ок, користувач просто повторно надішле місто.
"""

_last: dict[int, dict] = {}


def remember(user_id: int, city: str, lat: float, lon: float) -> None:
    _last[user_id] = {"city": city, "lat": lat, "lon": lon}


def recall(user_id: int) -> dict | None:
    return _last.get(user_id)
