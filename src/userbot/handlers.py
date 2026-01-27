from telethon import events, types
from src.services import GroupService
from src.database.client import get_db_session
from src.config import logger

async def sync_groups(client):
    """
    Проходит по всем диалогам аккаунта и добавляет группы в базу, если их там нет.
    """
    async with get_db_session() as session:
        service = GroupService(session)
        logger.info("🔍 Начинаю синхронизацию групп из аккаунта...")
        
        count = 0
        async for dialog in client.iter_dialogs():
            # Нам нужны только группы и супергруппы
            if dialog.is_group:
                existing = await service.get_group_by_telegram_id(dialog.id)
                if not existing:
                    await service.add_group(
                        telegram_id=dialog.id,
                        title=dialog.name,
                        tags=[]
                    )
                    count += 1
                    logger.info(f"➕ Добавлена новая группа: {dialog.name}")
        
        if count > 0:
            logger.info(f"✅ Синхронизация завершена. Добавлено групп: {count}")
        else:
            logger.info("ℹ️ Новых групп не обнаружено.")

def register_userbot_handlers(client):
    """
    Регистрация обработчиков событий для Userbot (Telethon)
    """
    @client.on(events.NewMessage)
    async def handle_new_message(event):
        # Здесь в будущем будет логика парсинга сообщений в стакан
        # Пока просто фильтруем только группы
        if event.is_group:
            # logger.debug(f"Получено сообщение из группы {event.chat_id}")
            pass
