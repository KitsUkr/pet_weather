"""Команди користувача: /start, погода за назвою міста, геолокація,
«Моя погода» та збереження улюбленого міста.
"""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import texts
from database import get_favorite, get_last_seen, set_favorite, set_last_seen
from service import build_weather_photo
from weather.client import WeatherError, geocode_city

logger = logging.getLogger(__name__)

router = Router()


# ══════════════════════════════════════════════════════════════════════════════
#   Клавіатури
# ══════════════════════════════════════════════════════════════════════════════

def _reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_GEO, request_location=True)],
            [KeyboardButton(text=texts.BTN_MY_WEATHER)],
        ],
        resize_keyboard=True,
    )


def _weather_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BTN_MAKE_FAV, callback_data="make_fav"),
            InlineKeyboardButton(text=texts.BTN_SUBSCRIBE_THIS, callback_data="sub_start"),
        ],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#   /start
# ══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        texts.START_WELCOME,
        reply_markup=_reply_kb(),
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#   Погода
# ══════════════════════════════════════════════════════════════════════════════

async def _send_weather(message: Message, city: str, lat: float, lon: float) -> None:
    """Будує картку й надсилає фото. Помилки показує текстом, не падає."""
    try:
        png, caption = await build_weather_photo(city, lat, lon)
    except WeatherError:
        await message.answer(texts.ERR_WEATHER_UNAVAILABLE)
        return
    except Exception as exc:
        logger.exception("Помилка рендеру погоди для '%s': %s", city, exc)
        await message.answer(texts.ERR_WEATHER_UNAVAILABLE)
        return

    await set_last_seen(message.chat.id, city, lat, lon)
    await message.answer_photo(
        BufferedInputFile(png, filename="weather.png"),
        caption=caption,
        reply_markup=_weather_actions_kb(),
    )


# «Моя погода» — reply-кнопка (текст збігається з BTN_MY_WEATHER)
@router.message(F.text == texts.BTN_MY_WEATHER)
async def msg_my_weather(message: Message):
    await _my_weather(message, message.from_user.id)


@router.callback_query(F.data == "my_weather")
async def cb_my_weather(callback: CallbackQuery):
    await _my_weather(callback.message, callback.from_user.id)
    await callback.answer()


async def _my_weather(message: Message, user_id: int) -> None:
    fav = await get_favorite(user_id)
    if fav is None:
        await message.answer(texts.NO_FAVORITE.format(btn=texts.BTN_MAKE_FAV))
        return
    await _send_weather(message, fav["city"], fav["lat"], fav["lon"])


# Геолокація (кнопка request_location працює лише в мобільному Telegram)
@router.message(F.location)
async def msg_location(message: Message):
    loc = message.location
    logger.info(
        "Геолокація від user=%s: %.4f, %.4f",
        message.from_user.id, loc.latitude, loc.longitude,
    )
    await _send_weather(message, "Ваше місцезнаходження", loc.latitude, loc.longitude)


# Місце (venue): якщо локацію поділили через 📎 і обрали конкретне місце,
# Telegram шле venue — message.location тут None, координати лежать у venue.location.
@router.message(F.venue)
async def msg_venue(message: Message):
    venue = message.venue
    name = venue.title or "Ваше місцезнаходження"
    logger.info("Venue від user=%s: %s", message.from_user.id, name)
    await _send_weather(
        message, name, venue.location.latitude, venue.location.longitude
    )


# Будь-який інший текст (не команда) трактуємо як назву міста
@router.message(F.text & ~F.text.startswith("/"))
async def msg_city(message: Message):
    name = message.text.strip()
    try:
        place = await geocode_city(name)
    except WeatherError:
        await message.answer(texts.ERR_WEATHER_UNAVAILABLE)
        return

    if place is None:
        await message.answer(texts.ERR_CITY_NOT_FOUND)
        return

    await _send_weather(message, place["name"], place["lat"], place["lon"])


# ══════════════════════════════════════════════════════════════════════════════
#   Улюблене місто
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "make_fav")
async def cb_make_fav(callback: CallbackQuery):
    last = await get_last_seen(callback.from_user.id)
    if last is None:
        await callback.answer(texts.NO_FAVORITE.format(btn=texts.BTN_MAKE_FAV), show_alert=True)
        return

    await set_favorite(callback.from_user.id, last["city"], last["lat"], last["lon"])
    await callback.answer(texts.FAV_SAVED.format(city=last["city"]), show_alert=True)
