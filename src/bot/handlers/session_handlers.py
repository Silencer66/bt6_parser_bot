from typing import List, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from datetime import datetime, timedelta, timezone

from services import SessionService, GroupService
from database import TradeDirection, PaymentMethod
from config import logger
from userbot.manager import UserbotManager

router = Router()


class CreateSessionStates(StatesGroup):
    waiting_for_direction = State()
    waiting_for_currency_from = State()
    waiting_for_currency_to = State()
    waiting_for_target_rate = State()
    waiting_for_volume = State()
    waiting_for_payment_method = State()
    waiting_for_ttl = State()


@router.message(Command("create_session"))
async def cmd_create_session(message: Message, state: FSMContext):
    """Начать создание заявки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Покупаю", callback_data="direction_buy"),
            InlineKeyboardButton(text="💰 Продаю", callback_data="direction_sell")
        ]
    ])
    
    await message.answer(
        "📊 <b>Создание торговой сессии</b>\n\n"
        "Выберите направление сделки:",
        reply_markup=keyboard
    )
    await state.set_state(CreateSessionStates.waiting_for_direction)


@router.callback_query(F.data.startswith("direction_"), CreateSessionStates.waiting_for_direction)
async def process_direction(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора направления"""
    direction = TradeDirection.BUY if callback.data == "direction_buy" else TradeDirection.SELL
    
    # Автоматически устанавливаем валюты
    if direction == TradeDirection.BUY:
        # Покупаю USDT за RUB
        currency_from = "USDT"
        currency_to = "RUB"
    else:
        # Продаю USDT за RUB
        currency_from = "RUB"
        currency_to = "USDT"
    
    await state.update_data(
        direction=direction.value,
        currency_from=currency_from,
        currency_to=currency_to
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить (парсить все)", callback_data="target_rate_skip")]
    ])
    
    await callback.message.edit_text(
        "📦 Введите целевой курс:\n\n"
        "💡 <i>Введите 0 или нажмите 'Пропустить', чтобы парсить все предложения без фильтрации</i>",
        reply_markup=keyboard
    )
    await state.set_state(CreateSessionStates.waiting_for_target_rate)
    await callback.answer()



@router.callback_query(F.data == "target_rate_skip", CreateSessionStates.waiting_for_target_rate)
async def process_target_rate_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск целевого курса"""
    await state.update_data(target_rate=0)
    
    await callback.message.edit_text(
        "📦 Введите объем сделки:"
    )
    await state.set_state(CreateSessionStates.waiting_for_volume)
    await callback.answer()


@router.message(CreateSessionStates.waiting_for_target_rate)
async def process_target_currency(message: Message, state: FSMContext):
    """Обработка целевого курса"""
    try:
        target_currency = float(message.text.strip())
        await state.update_data(target_rate=target_currency)
        
        await message.answer(
            "📦 Введите объем сделки:"
        )
        await state.set_state(CreateSessionStates.waiting_for_volume)
    except ValueError:
        await message.answer("❌ Введите корректное число для целевого курса.")

@router.message(CreateSessionStates.waiting_for_volume)
async def process_volume(message: Message, state: FSMContext):
    """Обработка объема"""
    volume = message.text.strip()
    await state.update_data(volume=volume)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Безнал БН", callback_data="payment_cashless")],
        [InlineKeyboardButton(text="Пропустить", callback_data="payment_skip")]
    ])
    
    await message.answer(
        "💳 Выберите метод оплаты (или пропустите):",
        reply_markup=keyboard
    )
    await state.set_state(CreateSessionStates.waiting_for_payment_method)


@router.callback_query(F.data.startswith("payment_"), CreateSessionStates.waiting_for_payment_method)
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    """Обработка метода оплаты"""
    if callback.data == "payment_cashless":
        await state.update_data(payment_method=PaymentMethod.CASHLESS.value)
    else:
        await state.update_data(payment_method=None)
    
    await callback.message.edit_text(
        "⏱️ Введите время жизни сессии в минутах (по умолчанию 60):"
    )
    await state.set_state(CreateSessionStates.waiting_for_ttl)
    await callback.answer()


@router.message(CreateSessionStates.waiting_for_ttl)
async def process_ttl(message: Message, state: FSMContext, session: AsyncSession, userbot: UserbotManager):
    """Обработка времени жизни и запуск рассылки"""
    try:
        ttl = int(message.text.strip()) if message.text.strip() else 60
        data = await state.get_data()
        
        # 1. Формирование красивого текста рассылки
        direction = TradeDirection(data["direction"])
        currency_from = data["currency_from"]
        currency_to = data["currency_to"]
        volume = data["volume"]
        target_rate = data["target_rate"]
        payment_method_enum = PaymentMethod(data["payment_method"]) if data.get("payment_method") else None
        
        # Шаблон сообщения в группы
        if direction == TradeDirection.BUY:
            broadcast_text = f"Коллеги, купим <b>{volume}</b> USDT"
        else:
            broadcast_text = f"Коллеги, продадим <b>{volume}</b> USDT"

        if target_rate and target_rate > 0:
            broadcast_text += f"\n\nЦелевой курс <b>{target_rate}</b>"

        # 2. Получаем активные группы
        group_service = GroupService(session)
        active_groups = await group_service.get_active_groups()
        
        chat_ids = []
        if active_groups:
           status_msg = await message.answer(f"🚀 Запускаю сессию! Рассылка в {len(active_groups)} групп...")
           for group in active_groups:
               try:
                   await userbot.client.send_message(entity=group.telegram_id, message=broadcast_text, parse_mode='html')
                   chat_ids.append(group.telegram_id)
                   await asyncio.sleep(1.0) # Анти-флуд
               except Exception as e:
                   logger.error(f"Broadcast error: {e}")
        else:
           await message.answer("⚠️ Нет активных групп для рассылки, но сессия создана локально.")

        # 3. Сохраняем сессию в БД (опционально, для истории)
        service = SessionService(session)
        await service.create_session(
            direction=direction,
            currency_from=currency_from,
            currency_to=currency_to,
            volume=volume,
            payment_method=payment_method_enum,
            time_to_live_minutes=ttl
        )

        # 4. Запускаем "Табло" (Broadcast Monitor)
        from utils.broadcast_state import broadcast_manager
        
        # Направление для менеджера: если мы BUY, то ищем продавцов, передаем 'buy'
        trade_dir_str = "buy" if direction == TradeDirection.BUY else "sell"
        
        broadcast_manager.start(
            admin_id=message.from_user.id, 
            duration_minutes=ttl, 
            target_chat_ids=chat_ids,
            direction=trade_dir_str,
            currency_from=currency_from,
            currency_to=currency_to,
            target_rate=target_rate
        )
        
        # Создаем сообщение-табло через бота (без entity в userbot — избегаем PeerUser not found)
        dashboard_preview = (
             f"📊 <b>Сбор заявок: {'ПОКУПКА' if direction == TradeDirection.BUY else 'ПРОДАЖА'}</b>\n"
             f"⏱️ Осталось времени: {ttl} мин.\n\n"
             f"⏳ Ожидаю первые офферы..."
        )
        
        try:
             dash_msg = await message.answer(dashboard_preview, parse_mode="html")
             broadcast_manager.set_report_message(message.chat.id, dash_msg.message_id, message.bot)
             await message.answer("✅ Сессия активна! Сводка выше будет обновляться в реальном времени.")
        except Exception as e:
             await message.answer(f"⚠️ Табло не создалось: {e}")

        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число минут.")
