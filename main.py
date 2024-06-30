import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from handlers import assistant, values, mood
from config import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_handler(message: Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ключевые ценности", callback_data="define_values")],
        [InlineKeyboardButton(text="Виртуальный ассистент", callback_data="assistant_response")],
        [InlineKeyboardButton(text="Определить настроение", callback_data="detect_mood")]
    ])
    await message.answer("Привет! Выберите функцию, которую вы хотите использовать:", reply_markup=markup)

async def main():
    bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(values.router)
    dp.include_router(assistant.router)
    dp.include_router(mood.router)

    dp.message.register(start_handler, Command("start"))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
