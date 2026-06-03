"""Підписка на щоденний прогноз: /subscribe, /unsubscribe та інлайн-вибір часу."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import texts
from config import DEFAULT_SUB_TIME
from database import (
    disable_subscription,
    get_favorite,
    get_last_seen,
    upsert_subscription,
)

logger = logging.getLogger(__name__)

router = Router()

# Готові варіанти часу для інлайн-вибору
_TIME_CHOICES = ["06:00", "07:00", "08:00", "09:00", "12:00", "18:00", "21:00"]


def _time_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, t in enumerate(_TIME_CHOICES, 1):
        row.append(InlineKeyboardButton(text=t, callback_data=f"subtime:{t}"))
        if i % 4 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _parse_time(value: str) -> str | None:
    """'8:5' / '08:05' → '08:05'; невалідне → None."""
    value = (value or "").strip()
    if ":" not in value:
        return None
    hh, _, mm = value.partition(":")
    try:
        h, m = int(hh), int(mm)
    except ValueError:
        return None
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return f"{h:02d}:{m:02d}"


async def _resolve_location(user_id: int) -> dict | None:
    """Місто для підписки: останнє показане місто з БД (інакше — None)."""
    return await get_last_seen(user_id)


# ══════════════════════════════════════════════════════════════════════════════
#   Інлайн-флоу (кнопка під карткою погоди)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "sub_start")
async def cb_sub_start(callback: CallbackQuery):
    last = await get_last_seen(callback.from_user.id)
    if last is None:
        await callback.answer(
            texts.SUB_NEED_CITY.format(btn=texts.BTN_SUBSCRIBE_THIS), show_alert=True
        )
        return

    await callback.message.answer(
        texts.SUB_CHOOSE_TIME.format(city=last["city"]),
        reply_markup=_time_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("subtime:"))
async def cb_sub_time(callback: CallbackQuery):
    chosen = _parse_time(callback.data.split(":", 1)[1])
    last = await get_last_seen(callback.from_user.id)
    if chosen is None or last is None:
        await callback.answer(
            texts.SUB_NEED_CITY.format(btn=texts.BTN_SUBSCRIBE_THIS), show_alert=True
        )
        return

    await upsert_subscription(
        callback.from_user.id, last["city"], last["lat"], last["lon"], chosen
    )
    await callback.message.edit_text(
        texts.SUB_SET.format(time=chosen, city=last["city"])
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
#   Команди
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, command: CommandObject):
    when = DEFAULT_SUB_TIME
    if command.args:
        parsed = _parse_time(command.args)
        if parsed is None:
            await message.answer(texts.ERR_BAD_TIME)
            return
        when = parsed

    loc = await _resolve_location(message.from_user.id)
    if loc is None:
        loc = await get_favorite(message.from_user.id)

    if loc is None:
        await message.answer(texts.SUB_NEED_CITY.format(btn=texts.BTN_SUBSCRIBE_THIS))
        return

    await upsert_subscription(
        message.from_user.id, loc["city"], loc["lat"], loc["lon"], when
    )
    await message.answer(texts.SUB_SET.format(time=when, city=loc["city"]))


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    was_active = await disable_subscription(message.from_user.id)
    await message.answer(texts.SUB_DISABLED if was_active else texts.SUB_NONE)
