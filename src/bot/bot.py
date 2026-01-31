from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from bot.handlers import group_handlers, session_handlers, base_handlers
from bot.middleware.db_middleware import DatabaseMiddleware
from bot.middleware.auth_middleware import AuthMiddleware
from config import Config


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

    # Auth Middleware (проверка пароля)
    dp.message.middleware(AuthMiddleware())
    
    # Регистрация роутеров (порядок важен!)
    # Специфичные роутеры должны быть ПЕРВЫМИ
    dp.include_router(group_handlers.router)
    dp.include_router(session_handlers.router)
    # Fallback роутер (catch-all) должен быть ПОСЛЕДНИМ
    dp.include_router(base_handlers.router)
    
    # Установка списка команд в меню бота
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="groups", description="Список групп"),
        BotCommand(command="update_groups", description="Обновить чаты из аккаунта"),
        BotCommand(command="create_session", description="Создать запрос"),
    ]
    await bot.set_my_commands(commands)
    
    return bot, dp
