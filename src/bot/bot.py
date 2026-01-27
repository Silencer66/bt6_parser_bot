from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.bot.handlers import group_handlers, session_handlers, base_handlers
from src.bot.middleware.db_middleware import DatabaseMiddleware
from src.config import Config


async def setup_bot():
    """Настройка и инициализация бота и диспетчера"""
    # Инициализация бота с новыми параметрами aiogram 3.7+
    bot = Bot(
        token=Config.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Регистрация роутеров
    dp.include_router(base_handlers.router)
    dp.include_router(group_handlers.router)
    dp.include_router(session_handlers.router)
    
    return bot, dp
