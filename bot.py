import asyncio
import logging
import logging.handlers
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

import scheduler as scheduler_module
import weather.client as weather_client
from config import BOT_TOKEN
from database import close_db, init_db
from handlers import fallback, group, subscription, user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            "bot.log",
            encoding="utf-8",
            maxBytes=5_000_000,
            backupCount=3,
        ),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Ініціалізація...")

    await init_db()
    logger.info("База даних ініціалізована")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(user.router)
    dp.include_router(subscription.router)
    dp.include_router(group.router)     # групові чати
    dp.include_router(fallback.router)  # має бути останнім — ловить усе інше

    # Команди працюють лише в особистих чатах, тож і в меню показуємо там
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Стартове повідомлення"),
            BotCommand(command="change", description="Змінити населений пункт"),
            BotCommand(command="subscribe", description="Щоранковий прогноз"),
            BotCommand(command="unsubscribe", description="Вимкнути розсилку"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )

    sched = scheduler_module.start(bot)

    logger.info("Бот запущено! Очікування повідомлень...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message"],
        )
    finally:
        scheduler_module.stop(sched)
        await bot.session.close()
        await weather_client.close()
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено")
