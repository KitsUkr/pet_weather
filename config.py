import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        sys.exit(f"Помилка: {name} не задано в .env файлі!")
    return value


BOT_TOKEN = _require("BOT_TOKEN")

DB_PATH = os.getenv("DB_PATH", "weather.db").strip() or "weather.db"

# Час за замовчуванням для /subscribe без аргументу (HH:MM, час київський).
DEFAULT_SUB_TIME = os.getenv("DEFAULT_SUB_TIME", "08:00").strip() or "08:00"

# Необов'язковий шлях до .ttf-шрифту з кирилицею (інакше системний fallback).
FONT_PATH = os.getenv("FONT_PATH", "").strip()

# Часовий пояс — уся логіка часу (прогноз, розсилка) рахується в київському часі.
TZ = "Europe/Kyiv"
