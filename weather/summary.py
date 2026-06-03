import datetime as dt

# Хмарність за WMO weather_code (для ясних/хмарних/туманних кодів).
_CLOUD_PHRASE = {
    0:  "Сьогодні ясно, небо чисте",
    1:  "Сьогодні переважно сонячно",
    2:  "Сьогодні мінлива хмарність, сонце час від часу визиратиме з-за хмар",
    3:  "Сьогодні переважно хмарно, сонце рідко визиратиме з-за хмар",
    45: "Сьогодні туманно",
    48: "Сьогодні туман з памороззю",
}
_CLOUD_DEFAULT = "Сьогодні хмарно"

# Опади: від найвагоміших/найнебезпечніших до найлегших (для вибору головного
# типу за день). Ожеледь (sleet) — високо, бо це небезпечно на дорогах.
_PRECIP_ORDER = ["storm", "sleet", "snow", "rain", "drizzle"]
_PRECIP_PHRASE = {
    None:      "Без опадів.",
    "drizzle": "Подекуди мряка.",
    "rain":    "Місцями дощ.",
    "snow":    "Місцями сніг.",
    "sleet":   "Можлива ожеледиця.",
    "storm":   "Можлива гроза.",
}


def summarize_today(current: dict, days: list[dict], hours: list[dict]) -> str:
    """Повертає короткий опис погоди на сьогодні (1–2 речення)."""
    today_code = days[0].get("code") if days else None
    if today_code is None:
        today_code = current.get("code")

    cloud = _CLOUD_PHRASE.get(today_code, _CLOUD_DEFAULT)
    precip = _PRECIP_PHRASE[_today_precip(current, days, hours, today_code)]
    return f"{cloud}. {precip}"


def _today_precip(current, days, hours, today_code) -> str | None:
    """Головний тип опадів за сьогоднішні години (None — без опадів)."""
    today = _date_of(current.get("time"))
    if today is None and days:
        today = _date_of(days[0].get("date"))

    kinds = set()
    for hour in hours or []:
        if today is not None and _date_of(hour.get("time")) != today:
            continue
        kind = _precip_kind(hour.get("code"))
        if kind:
            kinds.add(kind)

    if not kinds:  # немає погодинних даних — орієнтуємось на денний код
        kind = _precip_kind(today_code)
        if kind:
            kinds.add(kind)

    return next((k for k in _PRECIP_ORDER if k in kinds), None)


def _precip_kind(code) -> str | None:
    try:
        code = int(code)
    except (TypeError, ValueError):
        return None
    if code in (95, 96, 99):
        return "storm"
    if code in (56, 57, 66, 67):       # крижана мряка / крижаний дощ → ожеледь
        return "sleet"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (61, 63, 65, 80, 81, 82):
        return "rain"
    if code in (51, 53, 55):
        return "drizzle"
    return None


def _date_of(value) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
