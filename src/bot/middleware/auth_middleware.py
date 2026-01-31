from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import Config, logger
from database.models.common import User

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        logger.info("🔐 AuthMiddleware called")
        
        # Если это не сообщение, пропускаем (пока)
        if not isinstance(event, Message):
            logger.info("⏭️ Not a message, skipping auth")
            return await handler(event, data)

        user_id = event.from_user.id
        logger.info(f"👤 Checking auth for user {user_id}")
             
        # 2. Если пароль не установлен, доступ открыт всем
        if not Config.BOT_ACCESS_PASSWORD:
            logger.info("🔓 No password set, access is open")
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            logger.error("❌ No database session in middleware data!")
            return await handler(event, data)

        # 3. Проверяем наличие пользователя в БД
        try:
            stmt = select(User).where(User.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ DB error in auth check: {e}")
            return await handler(event, data)

        logger.info(f"🔍 User {user_id} found in DB: {bool(user)}")

        if user:
            logger.info(f"✅ User {user_id} authorized, proceeding")
            return await handler(event, data)
        
        else:
            input_password = (event.text or "").strip()
            logger.info(f"🔑 Checking password for new user {user_id}: '{input_password}' == '{Config.BOT_ACCESS_PASSWORD}'?")
            
            if input_password == Config.BOT_ACCESS_PASSWORD:
                logger.info(f"✅ Password correct! Creating user {user_id}")
                new_user = User(
                    telegram_id=user_id,
                    username=event.from_user.username,
                    full_name=event.from_user.full_name,
                    is_admin=False
                )
                session.add(new_user)
                await session.commit()
                
                await event.answer("✅ Пароль принят! Добро пожаловать.\nТеперь вы можете пользоваться ботом.")
                return
            else:
                logger.info(f"❌ Wrong password from user {user_id}")
                await event.answer("🔒 <b>Доступ ограничен.</b>\nПожалуйста, введите пароль доступа:", parse_mode="html")
                return 
