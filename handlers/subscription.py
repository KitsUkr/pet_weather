"""Підписка на щоденний прогноз: /subscribe [ГГ:ХХ] та /unsubscribe.

Основний шлях підписки — онбординг (handlers/user.py); команди лишаються
для зміни часу чи відписки.
"""

import logging
import re

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import texts
import ui
from config import DEFAULT_SUB_TIME
from database import (
    disable_subscription,
    get_favorite,
    get_last_seen,
    upsert_subscription,
)

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)  # підписки — лише в особистих

# «8», «08:00», «8:30», «8 30», «8.30» → година й (необов'язково) хвилини
_TIME_RE = re.compile(r"^(\d{1,2})(?:\D{1,3}(\d{1,2}))?$")


def parse_time(value: str) -> str | None:
    """Гнучкий розбір часу: '8' / '08:00' / '8 30' → 'HH:MM'; невалідне → None."""
    m = _TIME_RE.match((value or "").strip())
    if m is None:
        return None
    h, mnt = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= h < 24 and 0 <= mnt < 60):
        return None
    return f"{h:02d}:{mnt:02d}"


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, command: CommandObject):
    await ui.delete_user_message(message)

    when = DEFAULT_SUB_TIME
    if command.args:
        parsed = parse_time(command.args)
        if parsed is None:
            await ui.notify(message.bot, message.chat.id, texts.ERR_BAD_TIME)
            return
        when = parsed

    loc = await get_favorite(message.from_user.id) or await get_last_seen(message.from_user.id)
    if loc is None:
        await ui.notify(message.bot, message.chat.id, texts.SUB_NEED_CITY)
        return

    await upsert_subscription(
        message.from_user.id, loc["city"], loc["lat"], loc["lon"], when
    )
    await ui.notify(
        message.bot, message.chat.id,
        texts.SUB_SET.format(time=when, city=loc["city"]),
    )


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    await ui.delete_user_message(message)
    was_active = await disable_subscription(message.from_user.id)
    await ui.notify(
        message.bot, message.chat.id,
        texts.SUB_DISABLED if was_active else texts.SUB_NONE,
    )
