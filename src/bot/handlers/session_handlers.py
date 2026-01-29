from typing import List, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from datetime import datetime, timedelta

from services import SessionService, GroupService
from database import TradeDirection, PaymentMethod
from config import logger
from userbot.manager import UserbotManager

router = Router()


class CreateSessionStates(StatesGroup):
    waiting_for_direction = State()
    waiting_for_currency_from = State()
    waiting_for_currency_to = State()
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
    await state.update_data(direction=direction.value)
    
    await callback.message.edit_text(
        "💱 Введите валюту, которую вы хотите получить (например: USDT, RUB):"
    )
    await state.set_state(CreateSessionStates.waiting_for_currency_from)
    await callback.answer()


@router.message(CreateSessionStates.waiting_for_currency_from)
async def process_currency_from(message: Message, state: FSMContext):
    """Обработка валюты получения"""
    currency_from = message.text.strip().upper()
    await state.update_data(currency_from=currency_from)
    
    await message.answer(
        "💱 Введите валюту, которую вы отдаете (например: RUB, USD):"
    )
    await state.set_state(CreateSessionStates.waiting_for_currency_to)


@router.message(CreateSessionStates.waiting_for_currency_to)
async def process_currency_to(message: Message, state: FSMContext):
    """Обработка валюты отдачи"""
    currency_to = message.text.strip().upper()
    await state.update_data(currency_to=currency_to)
    
    await message.answer(
        "📦 Введите объем сделки (число, например: 10000):"
    )
    await state.set_state(CreateSessionStates.waiting_for_volume)


@router.message(CreateSessionStates.waiting_for_volume)
async def process_volume(message: Message, state: FSMContext):
    """Обработка объема"""
    try:
        volume = float(message.text.strip())
        await state.update_data(volume=volume)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Нерез", callback_data="payment_nonres"),
                InlineKeyboardButton(text="Нал", callback_data="payment_cash")
            ],
            [InlineKeyboardButton(text="Безнал", callback_data="payment_cashless")],
            [InlineKeyboardButton(text="Пропустить", callback_data="payment_skip")]
        ])
        
        await message.answer(
            "💳 Выберите метод оплаты (или пропустите):",
            reply_markup=keyboard
        )
        await state.set_state(CreateSessionStates.waiting_for_payment_method)
    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.callback_query(F.data.startswith("payment_"), CreateSessionStates.waiting_for_payment_method)
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    """Обработка метода оплаты"""
    payment_map = {
        "payment_nonres": PaymentMethod.NONRES,
        "payment_cash": PaymentMethod.CASH,
        "payment_cashless": PaymentMethod.CASHLESS
    }
    
    if callback.data != "payment_skip":
        payment_method = payment_map.get(callback.data)
        await state.update_data(payment_method=payment_method.value if payment_method else None)
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
        payment_method_enum = PaymentMethod(data["payment_method"]) if data.get("payment_method") else None
        
        # Определяем лейблы
        action = "ПОКУПАЮ" if direction == TradeDirection.BUY else "ПРОДАЮ"
        
        payment_method_str = "Любой"
        if payment_method_enum == PaymentMethod.NONRES: payment_method_str = "Безналичный расчет (Нерез)"
        elif payment_method_enum == PaymentMethod.CASH: payment_method_str = "Наличные"
        elif payment_method_enum == PaymentMethod.CASHLESS: payment_method_str = "Безналичный расчет"

        # Шаблон сообщения в группы
        broadcast_text = (
            f"🎯 <b>ИЩУ ЛИКВИДНОСТЬ | АКТИВНО ДО {(datetime.now() + timedelta(minutes=ttl)).strftime('%H:%M')}</b>\n\n"
            f"🔸 <b>НАПРАВЛЕНИЕ:</b> <b>{action} {currency_to} за {currency_from}</b>\n"
            f"🔸 <b>ОБЪЕМ:</b> <b>{volume:,.0f} {currency_to}</b>\n"
            f"🔸 <b>ОПЛАТА:</b> {payment_method_str}\n\n"
        )

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
            currency_to=currency_to
        )
        
        # Создаем сообщение-табло
        dashboard_preview = (
             f"📊 <b>Сбор заявок: {'ПОКУПКА' if direction == TradeDirection.BUY else 'ПРОДАЖА'}</b>\n"
             f"⏱️ Осталось времени: {ttl} мин.\n\n"
             f"⏳ Ожидаю первые офферы..."
        )
        
        try:
             # Отправляем через Userbot (чтобы он мог редактировать)
             dash_msg = await userbot.client.send_message(message.from_user.id, dashboard_preview, parse_mode='html')
             broadcast_manager.set_report_message_id(dash_msg.id)
             await message.answer("✅ Сессия активна! Сводка выше будет обновляться в реальном времени.")
        except Exception as e:
             await message.answer(f"⚠️ Табло не создалось: {e}")

        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число минут.")
