"""Останній роутер: ловить усе, що не оброблено вище.

Дає дві речі: зрозумілу відповідь користувачу замість тиші та запис у лог
типу повідомлення (content_type) — корисно для діагностики (наприклад, видно,
чи долітає геолокація і яким типом).
"""

import logging

from aiogram import Router
from aiogram.types import Message

import texts

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def catch_all(message: Message):
    user_id = message.from_user.id if message.from_user else "?"
    logger.info("Необроблене повідомлення user=%s, тип=%s", user_id, message.content_type)
    await message.answer(texts.UNKNOWN_MESSAGE)
