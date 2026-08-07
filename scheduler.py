"""Щоденна розсилка прогнозу через APScheduler.

Працює просто й надійно: щохвилини (на нульовій секунді) беремо поточний
київський час HH:MM і шлемо прогноз усім, у кого підписка саме на цей час.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TZ
from database import due_subscriptions
from service import build_weather_photo
from weather.client import WeatherError

logger = logging.getLogger(__name__)

_KYIV = ZoneInfo(TZ)


async def _broadcast(bot: Bot) -> None:
    hhmm = datetime.now(_KYIV).strftime("%H:%M")
    subs = await due_subscriptions(hhmm)
    if not subs:
        return

    logger.info("Розсилка о %s: %d підписників", hhmm, len(subs))
    for sub in subs:
        try:
            png, caption = await build_weather_photo(sub["city"], sub["lat"], sub["lon"])
            await bot.send_photo(
                sub["user_id"],
                BufferedInputFile(png, filename="weather.png"),
                caption=caption,
            )
        except WeatherError:
            logger.warning("Погода недоступна для підписки user=%s", sub["user_id"])
        except Exception as exc:
            # Найчастіше — користувач заблокував бота; не зупиняємо розсилку.
            logger.warning("Не вдалося надіслати user=%s: %s", sub["user_id"], exc)
        await asyncio.sleep(0.05)  # делікатно щодо лімітів Telegram


def start(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=_KYIV)
    scheduler.add_job(_broadcast, "cron", second=0, args=[bot], id="daily_broadcast")
    scheduler.start()
    logger.info("Планувальник розсилки запущено (TZ=%s)", TZ)
    return scheduler


def stop(scheduler: AsyncIOScheduler | None) -> None:
    if scheduler is not None:
        scheduler.shutdown(wait=False)
