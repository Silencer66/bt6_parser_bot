"""
Middleware для работы с БД
"""
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from database.client import get_db_session
from config import logger


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии БД"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        # Логируем входящее событие
        if isinstance(event, Message):
            logger.info(f"📩 Incoming message: {event.text} from {event.from_user.id}")

        try:
            async with get_db_session() as session:
                data["session"] = session
                data["db"] = session 
                return await handler(event, data)
        except Exception as e:
            logger.error(f"❌ Database middleware error: {e}", exc_info=True)
            if isinstance(event, Message):
                await event.answer("⚠️ Произошла ошибка при работе с базой данных.")
            return None
