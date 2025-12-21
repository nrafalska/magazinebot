# bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers.magazine import router as magazine_router


async def main():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ✅ Правильний спосіб встановити parse_mode в Aiogram 3.7+
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(magazine_router)

    logging.info("Bot started. Waiting for updates...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
