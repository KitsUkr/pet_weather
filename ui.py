"""Дрібні помічники для чистого чату.

Бот надсилає звичайні повідомлення (нічого не редагує). Повідомлення
користувача видаляються одразу, а службові відповіді — підтвердження й
помилки — показуються коротким сповіщенням, яке самознищується.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)

_NOTIFY_TTL = 5  # сек.: скільки живе службове сповіщення

# Тримаємо посилання на фонові задачі видалення, інакше їх збере GC
_pending_deletes: set[asyncio.Task] = set()


async def delete_user_message(message: Message) -> None:
    """Видаляє повідомлення користувача (мовчки, якщо не вдалося)."""
    try:
        await message.delete()
    except Exception as exc:
        logger.debug("Не вдалося видалити повідомлення користувача: %s", exc)


async def notify(bot: Bot, chat_id: int, text: str, ttl: int = _NOTIFY_TTL) -> None:
    """Коротке сповіщення-алерт: повідомлення, яке зникає через ttl секунд."""
    msg = await bot.send_message(chat_id, text)
    task = asyncio.create_task(_delete_later(bot, chat_id, msg.message_id, ttl))
    _pending_deletes.add(task)
    task.add_done_callback(_pending_deletes.discard)


async def _delete_later(bot: Bot, chat_id: int, message_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as exc:
        logger.debug("Не вдалося видалити сповіщення: %s", exc)
