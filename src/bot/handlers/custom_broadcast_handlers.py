from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from services import GroupService
from config import logger
from userbot.manager import UserbotManager
from utils.broadcast_state import broadcast_manager


router = Router()


class CustomBroadcastStates(StatesGroup):
    waiting_for_custom_text = State()
    waiting_for_ttl = State()


@router.message(Command("broadcast_custom"))
async def cmd_broadcast_custom(message: Message, state: FSMContext):
    """Начать создание кастомной рассылки"""
    await message.answer(
        "📝 <b>Создание произвольной рассылки</b>\n\n"
        "Введите текст сообщения, которое будет отправлено в группы:"
    )
    await state.set_state(CustomBroadcastStates.waiting_for_custom_text)


@router.message(CustomBroadcastStates.waiting_for_custom_text)
async def process_custom_text(message: Message, state: FSMContext):
    """Обработка кастомного текста"""
    custom_text = message.text.strip()
    await state.update_data(custom_text=custom_text)
    
    await message.answer(
        "⏱️ Введите время жизни сессии в минутах (по умолчанию 60):"
    )
    await state.set_state(CustomBroadcastStates.waiting_for_ttl)


@router.message(CustomBroadcastStates.waiting_for_ttl)
async def process_custom_ttl(message: Message, state: FSMContext, session: AsyncSession, userbot: UserbotManager):
    """Обработка времени жизни и запуск кастомной рассылки"""
    try:
        ttl = int(message.text.strip()) if message.text.strip() else 60
        data = await state.get_data()
        custom_text = data["custom_text"]
        
        # Получаем активные группы
        group_service = GroupService(session)
        active_groups = await group_service.get_active_groups()
        
        chat_ids = []
        if active_groups:
            status_msg = await message.answer(f"🚀 Запускаю рассылку в {len(active_groups)} групп...")
            for group in active_groups:
                try:
                    await userbot.client.send_message(entity=group.telegram_id, message=custom_text, parse_mode='html')
                    chat_ids.append(group.telegram_id)
                    await asyncio.sleep(1.0)  # Анти-флуд
                except Exception as e:
                    logger.error(f"Broadcast error: {e}")
        else:
            await message.answer("⚠️ Нет активных групп для рассылки.")
            await state.clear()
            return
        
        # Запускаем мониторинг в кастомном режиме
        broadcast_manager.start(
            admin_id=message.from_user.id,
            duration_minutes=ttl,
            target_chat_ids=chat_ids,
            direction='buy',  # Dummy value
            currency_from='N/A',  # Dummy value
            currency_to='N/A',  # Dummy value
            is_custom=True  # ВАЖНО: включаем кастомный режим
        )
        
        # Создаем сообщение-табло через бота (без entity в userbot — избегаем PeerUser not found)
        dashboard_preview = (
            f"📊 <b>Сбор ответов: ПРОИЗВОЛЬНЫЙ ЗАПРОС</b>\n"
            f"⏱️ Осталось времени: {ttl} мин.\n\n"
            f"⏳ Ожидаю первые ответы..."
        )
        
        try:
            dash_msg = await message.answer(dashboard_preview, parse_mode="html")
            broadcast_manager.set_report_message(message.chat.id, dash_msg.message_id, message.bot)
            await message.answer("✅ Рассылка активна! Сводка выше будет обновляться в реальном времени.")
        except Exception as e:
            await message.answer(f"⚠️ Табло не создалось: {e}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число минут.")
