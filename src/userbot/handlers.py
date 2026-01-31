from telethon import events, types
from services import GroupService
from database.client import get_db_session
from datetime import datetime
from utils.broadcast_state import broadcast_manager
from api.openrouter.client import ai_client
from config import logger

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
        """Main entry point for all messages"""
        if not event.is_group:
            return
        
        if not broadcast_manager.is_monitoring(event.chat_id):
            return
        
        if broadcast_manager.is_custom_mode:
            await handle_custom_broadcast_message(event, client)
        else:
            await handle_structured_broadcast_message(event, client)


async def handle_structured_broadcast_message(event, client):
    """Handle messages for structured trading sessions"""
    my_direction = broadcast_manager.session_direction
    currency_from = broadcast_manager.currency_from
    currency_to = broadcast_manager.currency_to
    
    context_prompt = ""
    if my_direction == 'buy':
        context_prompt = (
            f"Мы ищем тех, кто ПРОДАЕТ {currency_to} за {currency_from}. "
            f"Нам нужны только предложения на ПРОДАЖУ (side='sell'). "
            f"Игнорируй тех, кто тоже хочет купить."
        )
    elif my_direction == 'sell':
        context_prompt = (
            f"Мы ищем тех, кто ПОКУПАЕТ {currency_to} за {currency_from}. "
            f"Нам нужны только предложения на ПОКУПКУ (side='buy'). "
            f"Игнорируй тех, кто тоже хочет продать."
        )

    offers = await ai_client.analyze_message(event.text, context_prompt=context_prompt)
    
    if ai_client.api_key and offers is None:
        return

    try:
        chat = await event.get_chat()
        sender = await event.get_sender()
        sender_name = getattr(sender, 'first_name', 'Unknown')
        username = getattr(sender, 'username', 'no_username')
        user_link = f"@{username}" if username != 'no_username' else sender_name
        chat_title = getattr(chat, 'title', 'Unknown Group')

        text_line = event.text[:100].replace('\n', ' ')
        
        # Process each offer from the list
        for offer in offers:
            broadcast_manager.add_response(
                user=user_link, 
                group=chat_title, 
                text=text_line,
                price=offer.get('price'),
                volume=offer.get('volume'),
                side=offer.get('side'),
                raw_text=event.text
            )
        
        # Update dashboard
        await update_dashboard(client)

    except Exception as e:
        logger.error(f"Error handling structured broadcast message: {e}")


async def handle_custom_broadcast_message(event, client):
    """Handle messages for custom broadcasts (no direction filtering)"""
    context_prompt = (
        "Извлеки торговые предложения из сообщения. "
        "Принимай ВСЕ предложения (и покупку, и продажу). "
        "Игнорируй только явный спам и нерелевантные сообщения."
    )
    
    offers = await ai_client.analyze_message(event.text, context_prompt=context_prompt)
    
    if ai_client.api_key and offers is None:
        return
    
    if not ai_client.api_key:
        offers = [{"side": None, "price": None, "volume": None}]
    
    try:
        chat = await event.get_chat()
        sender = await event.get_sender()
        sender_name = getattr(sender, 'first_name', 'Unknown')
        username = getattr(sender, 'username', 'no_username')
        user_link = f"@{username}" if username != 'no_username' else sender_name
        chat_title = getattr(chat, 'title', 'Unknown Group')
        
        # Process each offer from the list
        for offer in offers:
            broadcast_manager.add_response(
                user=user_link,
                group=chat_title,
                text=event.text[:100].replace('\n', ' '),
                price=offer.get('price'),
                volume=offer.get('volume'),
                side=offer.get('side'),
                raw_text=event.text
            )
        
        # Update dashboard
        await update_dashboard(client)
        
    except Exception as e:
        logger.error(f"Error handling custom broadcast message: {e}")


async def update_dashboard(client):
    """Update the dashboard message"""
    if broadcast_manager.report_message_id and broadcast_manager.admin_id:
        dashboard_content = broadcast_manager.get_dashboard_text()
        
        minutes_left = 0
        if broadcast_manager.end_time:
            minutes_left = int((broadcast_manager.end_time - datetime.now()).total_seconds() / 60)
        
        if broadcast_manager.is_custom_mode:
            direction_str = "ПРОИЗВОЛЬНЫЙ ЗАПРОС"
        else:
            my_direction = broadcast_manager.session_direction
            direction_str = "ПОКУПКА" if my_direction == 'buy' else "ПРОДАЖА"

        new_text = (
            f"📊 <b>Сбор заявок: {direction_str}</b>\n"
            f"⏱️ Осталось времени: {minutes_left} мин.\n\n"
            f"{dashboard_content}\n"
        )
        
        try:
            await client.edit_message(
                entity=broadcast_manager.admin_id,
                message=broadcast_manager.report_message_id,
                text=new_text,
                parse_mode='html'
            )
        except Exception as edit_err:
            logger.warning(f"Failed to update dashboard: {edit_err}")
