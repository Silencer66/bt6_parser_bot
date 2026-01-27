"""
Обработчики для управления торговыми сессиями
"""
from typing import List, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.services import SessionService, OrderBookService
from src.database import TradeDirection, PaymentMethod, SessionStatus

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
    """Начать создание торговой сессии"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Покупаю", callback_data="direction_buy"),
            InlineKeyboardButton(text="💰 Продаю", callback_data="direction_sell")
        ]
    ])
    
    await message.answer(
        "📊 <b>Создание торговой сессии</b>\n\n"
        "Выберите направление сделки:",
        reply_markup=keyboard,
        parse_mode="Markdown"
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
async def process_ttl(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка времени жизни и создание сессии"""
    try:
        ttl = int(message.text.strip()) if message.text.strip() else 60
        data = await state.get_data()
        
        service = SessionService(session)
        trading_session = await service.create_session(
            direction=TradeDirection(data["direction"]),
            currency_from=data["currency_from"],
            currency_to=data["currency_to"],
            volume=data["volume"],
            payment_method=PaymentMethod(data["payment_method"]) if data.get("payment_method") else None,
            time_to_live_minutes=ttl
        )
        
        await message.answer(
            f"✅ <b>Торговая сессия создана!</b>\n\n"
            f"ID: {trading_session.id}\n"
            f"Направление: {'Покупка' if trading_session.direction == TradeDirection.BUY else 'Продажа'}\n"
            f"Пара: {trading_session.currency_from}/{trading_session.currency_to}\n"
            f"Объем: {trading_session.volume}\n"
            f"Время жизни: {ttl} мин.\n\n"
            f"Используйте /activate_session {trading_session.id} для активации."
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число минут.")


@router.message(Command("activate_session"))
async def cmd_activate_session(message: Message, session: AsyncSession):
    """Активировать торговую сессию"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise IndexError
        session_id = int(parts[1])
        service = SessionService(session)
        trading_session = await service.activate_session(session_id)
        
        if trading_session:
            await message.answer(
                f"✅ <b>Сессия {session_id} активирована!</b>\n\n"
                f"Направление: {'Покупка' if trading_session.direction == TradeDirection.BUY else 'Продажа'}\n"
                f"Пара: {trading_session.currency_from}/{trading_session.currency_to}\n"
                f"Время жизни: {trading_session.time_to_live_minutes} мин.\n\n"
                f"Сессия будет собирать заявки до истечения времени."
            )
        else:
            await message.answer(f"❌ Сессия {session_id} не найдена.")
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /activate_session <session_id>")


@router.message(Command("order_book"))
async def cmd_order_book(message: Message, session: AsyncSession):
    """Показать стакан заявок для активной сессии"""
    service = SessionService(session)
    order_book_service = OrderBookService(session)
    
    active_sessions = await service.get_active_sessions()
    
    if not active_sessions:
        await message.answer("❌ Нет активных сессий.")
        return
    
    # Берем первую активную сессию
    trading_session = active_sessions[0]
    order_book = await order_book_service.build_order_book(trading_session.id)
    text = order_book_service.format_order_book_text(order_book, trading_session)
    
    await message.answer(text)
