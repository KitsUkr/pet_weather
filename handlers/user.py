"""Мінімалістичний флоу користувача.

Онбординг: /start → «введіть населений пункт» → «хочете щоранковий прогноз?»
(година або «ні»). Далі будь-який текст — назва міста, геолокація — погода
поруч. Повідомлення користувача видаляються; бот надсилає звичайні
повідомлення, а службові відповіді показує сповіщенням (див. ui.py).
"""

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message

import texts
import ui
from database import (
    get_favorite,
    get_subscription,
    set_favorite,
    set_last_seen,
    upsert_subscription,
)
from handlers.subscription import parse_time
from service import build_weather_photo
from weather.client import WeatherError, geocode_city

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)  # групи — handlers/group.py

_GEO_NAME = "Ваше місцезнаходження"

# Відповіді, які трактуємо як відмову від щоденної розсилки
_NO_WORDS = {"ні", "нi", "нет", "не", "не хочу", "no", "-"}


class Onboarding(StatesGroup):
    city = State()   # чекаємо назву населеного пункту
    daily = State()  # чекаємо годину розсилки або «ні»


# ══════════════════════════════════════════════════════════════════════════════
#   Онбординг
# ══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Новому користувачу — привітання й онбординг; знайомому — стартове
    повідомлення з його збереженим пунктом (без повторного налаштування)."""
    await ui.delete_user_message(message)

    fav = await get_favorite(message.from_user.id)
    if fav is None:
        await state.set_state(Onboarding.city)
        await message.answer(texts.START_NEW)
        return

    await state.clear()
    sub = await get_subscription(message.from_user.id)
    if sub is not None and sub["is_active"]:
        sub_line = texts.START_SUB_ON.format(time=sub["send_time"])
    else:
        sub_line = texts.START_SUB_OFF
    await message.answer(texts.START_BACK.format(city=fav["city"], sub=sub_line))


@router.message(Command("change"))
async def cmd_change(message: Message, state: FSMContext):
    """Змінити збережений населений пункт — заново проходимо онбординг."""
    await ui.delete_user_message(message)
    await state.set_state(Onboarding.city)
    await message.answer(texts.ASK_CITY)


@router.message(Onboarding.city, F.text & ~F.text.startswith("/"))
async def onb_city(message: Message, state: FSMContext):
    await ui.delete_user_message(message)
    try:
        place = await geocode_city(message.text)
    except WeatherError:
        await ui.notify(message.bot, message.chat.id, texts.ERR_WEATHER_UNAVAILABLE)
        return

    if place is None:
        await ui.notify(message.bot, message.chat.id, texts.CITY_RETRY)
        return

    await _save_home(message.from_user.id, place["name"], place["lat"], place["lon"])
    await state.set_state(Onboarding.daily)
    await message.answer(texts.ASK_DAILY.format(city=place["name"]))


@router.message(Onboarding.daily, F.text & ~F.text.startswith("/"))
async def onb_daily(message: Message, state: FSMContext):
    await ui.delete_user_message(message)

    fav = await get_favorite(message.from_user.id)
    if fav is None:  # БД скинули посеред онбордингу — починаємо заново
        await state.set_state(Onboarding.city)
        await message.answer(texts.ASK_CITY)
        return

    answer = message.text.strip().lower().strip("«»\"'.!")
    if answer in _NO_WORDS:
        await state.clear()
        await _send_weather(message.bot, message.chat.id, fav["city"], fav["lat"], fav["lon"])
        return

    when = parse_time(message.text)
    if when is None:
        await ui.notify(message.bot, message.chat.id, texts.DAILY_RETRY)
        return

    await upsert_subscription(
        message.from_user.id, fav["city"], fav["lat"], fav["lon"], when
    )
    await state.clear()
    await _send_weather(
        message.bot, message.chat.id, fav["city"], fav["lat"], fav["lon"],
        note=texts.SUB_NOTE.format(time=when),
    )


# ══════════════════════════════════════════════════════════════════════════════
#   Погода
# ══════════════════════════════════════════════════════════════════════════════

async def _send_weather(
    bot: Bot, chat_id: int, city: str, lat: float, lon: float, note: str | None = None
) -> None:
    """Будує картку й надсилає фото. Помилки — сповіщенням, не падає."""
    try:
        png, caption = await build_weather_photo(city, lat, lon)
    except WeatherError:
        await ui.notify(bot, chat_id, texts.ERR_WEATHER_UNAVAILABLE)
        return
    except Exception as exc:
        logger.exception("Помилка рендеру погоди для '%s': %s", city, exc)
        await ui.notify(bot, chat_id, texts.ERR_WEATHER_UNAVAILABLE)
        return

    if note:
        caption = f"{caption}\n\n{note}"
    await set_last_seen(chat_id, city, lat, lon)
    await bot.send_photo(
        chat_id, BufferedInputFile(png, filename="weather.png"), caption=caption
    )


async def _save_home(user_id: int, city: str, lat: float, lon: float) -> None:
    await set_favorite(user_id, city, lat, lon)
    await set_last_seen(user_id, city, lat, lon)


# Геолокація або місце (venue — коли локацію поділили через 📎).
# Під час онбордингу приймаємо її як населений пункт, інакше показуємо погоду.
@router.message(F.location | F.venue)
async def msg_location(message: Message, state: FSMContext):
    await ui.delete_user_message(message)

    if message.venue is not None:
        name = message.venue.title or _GEO_NAME
        loc = message.venue.location
    else:
        name = _GEO_NAME
        loc = message.location
    logger.info("Локація від user=%s: %.4f, %.4f",
                message.from_user.id, loc.latitude, loc.longitude)

    if await state.get_state() == Onboarding.city.state:
        await _save_home(message.from_user.id, name, loc.latitude, loc.longitude)
        await state.set_state(Onboarding.daily)
        await message.answer(texts.ASK_DAILY.format(city=name))
        return

    await state.clear()
    await _send_weather(message.bot, message.chat.id, name, loc.latitude, loc.longitude)


# Будь-який інший текст (не команда) трактуємо як назву міста
@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def msg_city(message: Message):
    await ui.delete_user_message(message)
    try:
        place = await geocode_city(message.text)
    except WeatherError:
        await ui.notify(message.bot, message.chat.id, texts.ERR_WEATHER_UNAVAILABLE)
        return

    if place is None:
        await ui.notify(message.bot, message.chat.id, texts.CITY_RETRY)
        return

    await _send_weather(
        message.bot, message.chat.id, place["name"], place["lat"], place["lon"]
    )
