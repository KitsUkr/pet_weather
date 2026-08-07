"""Останній роутер: ловить усе, що не оброблено вище.

Видаляє повідомлення користувача (як і всюди) та показує коротку підказку
в єдиному повідомленні бота. Тип повідомлення пишемо в лог — корисно для
діагностики (наприклад, видно, чи долітає геолокація і яким типом).
"""

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

import texts
import ui

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)  # у групах мовчимо


@router.message()
async def catch_all(message: Message):
    user_id = message.from_user.id if message.from_user else "?"
    logger.info("Необроблене повідомлення user=%s, тип=%s", user_id, message.content_type)
    await ui.delete_user_message(message)
    await ui.notify(message.bot, message.chat.id, texts.UNKNOWN_MESSAGE)
