"""
Базовые обработчики команд
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await message.answer(
        "🤖 <b>Добро пожаловать в Telegram Parser Bot!</b>\n\n"
        "Этот бот помогает собирать и агрегировать ликвидность из OTC групп через Userbot.\n\n"
        "<b>Основные команды:</b>\n"
        "/groups — Просмотр отслеживаемых групп\n"
        "/create_session — Создать запрос\n"
        "/help — Справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    await message.answer(
        "📖 <b>Справка по командам</b>\n\n"
        "<b>Управление:</b>\n"
        "• /groups — Список всех отслеживаемых групп\n"
        "• /create_session — Создать запрос сбора ликвидности\n"
        "<b>Дополнительно:</b>\n"
        "• /start — Начать работу с ботом\n"
        "• /help — Показать эту справку"
    )
