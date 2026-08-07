"""Погода в групових чатах.

Флоу: хтось пише «єПогода ...» → бот реплаєм просить уточнити місто →
той самий користувач відповідає реплаєм на це прохання назвою міста →
бот надсилає картку погоди.

Щоб бот бачив звичайні (не командні) повідомлення в групі, у BotFather
треба вимкнути privacy mode: /setprivacy → Disable. Реплаї на повідомлення
бота долітають і з увімкненим privacy mode, а от саме слово-тригер — ні.
"""

import html
import logging
import re

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import BufferedInputFile, Message, User

import texts
from service import build_weather_photo
from weather.client import WeatherError, geocode_city

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))

# Слово-тригер окремим словом у будь-якому місці повідомлення.
# Терпимо ставимося до «епогода» через звичайне «е».
_TRIGGER = re.compile(r"(?<!\w)[єе]погода(?!\w)", re.IGNORECASE)

# Чекаємо на уточнення міста: (chat_id, id повідомлення бота) -> хто питав.
# Тримаємо в пам'яті: після рестарту користувач просто напише тригер знову.
_pending: dict[tuple[int, int], int] = {}
_PENDING_MAX = 500


def _remember_ask(chat_id: int, bot_msg_id: int, user_id: int) -> None:
    if len(_pending) >= _PENDING_MAX:
        _pending.pop(next(iter(_pending)))  # найстаріше прохання
    _pending[(chat_id, bot_msg_id)] = user_id


def _display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return html.escape(user.full_name)


@router.message(F.text.func(lambda t: bool(_TRIGGER.search(t))))
async def group_trigger(message: Message):
    """Слово-тригер у групі — просимо уточнити місто реплаєм."""
    ask = await message.reply(
        texts.GROUP_ASK_CITY.format(name=_display_name(message.from_user))
    )
    _remember_ask(message.chat.id, ask.message_id, message.from_user.id)


@router.message(F.reply_to_message, F.text & ~F.text.startswith("/"))
async def group_city(message: Message):
    """Реплай на прохання бота — трактуємо як назву міста.

    Реагуємо лише на реплаї від того, кого питали: чужі повідомлення в групі
    мовчки ігноруємо, щоб не шуміти.
    """
    key = (message.chat.id, message.reply_to_message.message_id)
    if _pending.get(key) != message.from_user.id:
        return

    try:
        place = await geocode_city(message.text)
    except WeatherError:
        await message.reply(texts.ERR_WEATHER_UNAVAILABLE)
        return

    if place is None:
        retry = await message.reply(texts.GROUP_CITY_RETRY)
        _pending.pop(key, None)
        _remember_ask(message.chat.id, retry.message_id, message.from_user.id)
        return

    _pending.pop(key, None)
    try:
        png, caption = await build_weather_photo(
            place["name"], place["lat"], place["lon"]
        )
    except WeatherError:
        await message.reply(texts.ERR_WEATHER_UNAVAILABLE)
        return
    except Exception as exc:
        logger.exception("Помилка рендеру погоди для '%s': %s", place["name"], exc)
        await message.reply(texts.ERR_WEATHER_UNAVAILABLE)
        return

    await message.reply_photo(
        BufferedInputFile(png, filename="weather.png"), caption=caption
    )
