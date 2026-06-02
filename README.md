# WeatherBot — погода України з карткою-картинкою

Telegram-бот, який показує прогноз погоди для українських міст у вигляді
згенерованої **картинки** (інфографіка). Дані — [Open-Meteo](https://open-meteo.com)
(безкоштовно, без API-ключа), рендер картки — Pillow.

## Можливості
- 🌤 Прогноз за назвою міста (просто напиши «Київ», «Львів», «Одеса»…).
- 📍 Прогноз за геолокацією (кнопка «Надіслати геолокацію»).
- ⭐ Збереження улюбленого міста + кнопка «Моя погода».
- 🔔 Щоденна розсилка прогнозу о вибраній годині (`/subscribe ГГ:ХХ`, `/unsubscribe`).

## Стек
- Python 3.12+, **aiogram 3.x** (long polling)
- Open-Meteo (geocoding + forecast) через `aiohttp`
- **Pillow** — рендер картки у PNG
- **APScheduler** — щоденна розсилка (час київський)
- **SQLite** через `aiosqlite` (улюблене місто + підписки)

## Структура
```
bot.py            entrypoint: polling + старт планувальника
config.py         завантаження .env
service.py        погода + рендер картки (спільне для хендлерів і розсилки)
state.py          in-memory «останнє показане місто»
database.py       SQLite: улюблене місто + підписки
scheduler.py      APScheduler: щоденна розсилка
texts.py          усі тексти UI (українською)
weather/          client.py (Open-Meteo) + codes.py (WMO-коди)
render/           card.py + icons.py + fonts.py (Pillow)
handlers/         user.py + subscription.py
```

## Запуск локально (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # впиши BOT_TOKEN від @BotFather
python bot.py
```
Шрифт для картки на Windows підхоплюється автоматично (Arial/Segoe UI).
За потреби вкажи свій `.ttf` через `FONT_PATH` у `.env`.

## Запуск у Docker
```bash
cp .env.example .env        # впиши BOT_TOKEN
docker compose up --build
```
У контейнері ставиться `fonts-dejavu-core`, тож кирилиця на картці малюється.
База (`weather.db`) зберігається у томі `./data`.

## Де взяти BOT_TOKEN
Напиши [@BotFather](https://t.me/BotFather) → `/newbot` → отримаєш токен →
встав у `.env` як `BOT_TOKEN=...`.

## Швидка перевірка картки без Telegram
```bash
python -c "import asyncio, service; png,_=asyncio.run(service.build_weather_photo('Київ',50.45,30.52)); open('test_card.png','wb').write(png)"
```
Відкрий `test_card.png` — переконайся, що кирилиця та іконки рендеряться.

## Примітки
- Іконки погоди малюються примітивами Pillow (self-contained, без бінарних
  ассетів). Точка розширення для PNG-набору — `render/icons.py`.
- БД — SQLite для простоти. За бажання легко замінити на PostgreSQL + `asyncpg`
  (як у проєкті UaAniSub), переписавши `database.py`.
