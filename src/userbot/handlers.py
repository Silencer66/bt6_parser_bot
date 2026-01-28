from telethon import events, types
from src.services import GroupService
from src.database.client import get_db_session
from datetime import datetime
from src.utils.broadcast_state import broadcast_manager
from src.api.openrouter.client import ai_client
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
        # 1. Проверяем, активен ли режим прослушки (Broadcast Monitoring)
        # Передаем ID чата, чтобы убедиться, что это одна из целевых групп
        if event.is_group and broadcast_manager.is_monitoring(event.chat_id):
            
            # --- AI ANALYZER ---
            # Определяем контекст для AI: чего мы хотим
            my_direction = broadcast_manager.session_direction # 'buy' или 'sell'
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

            # Проверяем, настроен ли AI и валидируем сообщение
            ai_data = await ai_client.analyze_message(event.text, context_prompt=context_prompt)
            
            # Если AI активен и вернул None (значит счел спамом или нерелевантной стороной) - игнорируем
            if ai_client.api_key and ai_data is None:
                # logger.debug(f"Filtered spam/irrelevant: {event.text[:50]}...")
                return

            try:
                # Получаем информацию о чате и отправителе
                chat = await event.get_chat()
                sender = await event.get_sender()
                sender_name = getattr(sender, 'first_name', 'Unknown')
                username = getattr(sender, 'username', 'no_username')
                user_link = f"@{username}" if username != 'no_username' else sender_name
                chat_title = getattr(chat, 'title', 'Unknown Group')

                # Формируем строку для лога (на всякий случай)
                text_line = event.text[:100].replace('\n', ' ')
                
                # Сохраняем структурированные данные
                broadcast_manager.add_response(
                    user=user_link, 
                    group=chat_title, 
                    text=text_line,
                    price=ai_data.get('price') if ai_data else None,
                    volume=ai_data.get('volume') if ai_data else None,
                    side=ai_data.get('side') if ai_data else None,
                    raw_text=event.text
                )
                
                # Обновляем Табло (сообщение у админа)
                if broadcast_manager.report_message_id and broadcast_manager.admin_id:
                    # Генерируем умный текст табло
                    dashboard_content = broadcast_manager.get_dashboard_text()
                    
                    minutes_left = 0
                    if broadcast_manager.end_time:
                         minutes_left = int((broadcast_manager.end_time - datetime.now()).total_seconds() / 60)
                         
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

            except Exception as e:
                logger.error(f"Ошибка при обработке ответа: {e}")

        # Здесь в будущем будет логика парсинга сообщений в стакан
        # Пока просто фильтруем только группы
        if event.is_group:
            # logger.debug(f"Получено сообщение из группы {event.chat_id}")
            pass
