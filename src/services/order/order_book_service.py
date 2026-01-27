from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .db_methods import DBMethods
from .models import OrderBook, OrderBookEntry
from src.database.models.common import (
    Order, 
    OrderStatus, 
    TradingSession, 
    PaymentMethod, 
    TradeDirection
)

class OrderBookService:
    """Сервис для работы со стаканом заявок"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.db_methods = DBMethods(session)

    async def build_order_book(self, session_id: int) -> OrderBook:
        """Построить стакан заявок для сессии"""
        trading_session = await self.db_methods.get_session_by_id(session_id)
        if not trading_session:
            return OrderBook(session_id=session_id, orders=[])

        # Получаем все валидные ордера сессии
        orders = await self.db_methods.get_by_session(session_id)
        
        valid_orders = [
            order for order in orders
            if order.is_valid() and order.matches_session(trading_session)
            and order.status == OrderStatus.PENDING
        ]

        # Сортируем по выгодности (для покупки - по возрастанию цены, для продажи - по убыванию)
        if trading_session.direction == TradeDirection.BUY:
            valid_orders.sort(key=lambda x: x.price)
        else:
            valid_orders.sort(key=lambda x: -x.price)

        # Создаем записи стакана
        entries = []
        for idx, order in enumerate(valid_orders, 1):
            group = await self.db_methods.get_group_by_id(order.group_id)
            group_name = group.title if group else "Unknown"
            
            entries.append(OrderBookEntry(
                order=order,
                rank=idx,
                group_name=group_name
            ))

        return OrderBook(session_id=session_id, orders=entries)

    def format_order_book_text(self, order_book: OrderBook, trading_session: TradingSession) -> str:
        """Форматировать стакан в текстовый вид"""
        direction_text = "ПОКУПКА" if trading_session.direction == TradeDirection.BUY else "ПРОДАЖА"
        currency_text = f"{trading_session.currency_from} (за {trading_session.currency_to}"
        
        if trading_session.payment_method:
            payment_map = {
                PaymentMethod.NONRES: "Нерез",
                PaymentMethod.CASH: "Нал",
                PaymentMethod.CASHLESS: "Безнал"
            }
            payment_text = payment_map.get(trading_session.payment_method, "")
            currency_text += f" {payment_text}"
        currency_text += ")"

        # Вычисляем оставшееся время
        delta = datetime.utcnow() - trading_session.created_at
        remaining = trading_session.time_to_live_minutes * 60 - delta.total_seconds()
        
        if remaining > 0:
            minutes = int(remaining / 60)
            time_left = f"Осталось времени: {minutes} мин."
        else:
            time_left = "Время истекло"

        lines = [
            f"📊 Сбор заявок: {direction_text} {currency_text}",
            time_left,
            "",
            "ТОП ПРЕДЛОЖЕНИЙ (Сортировка по выгодности):"
        ]

        top_orders = order_book.get_top_orders(10)
        for entry in top_orders:
            username = f"@{entry.order.username}" if entry.order.username else f"ID:{entry.order.user_id}"
            lines.append(
                f"{entry.rank}. {entry.display_price} | {entry.display_volume} | {username} ({entry.group_name})"
            )

        if order_book.total_volume > 0:
            lines.append("")
            lines.append(f"Всего объем в стакане: {order_book.total_volume:,.0f} {trading_session.currency_from}")
            lines.append(f"Средневзвешенный курс: {order_book.weighted_average_price:.2f}")

        return "\n".join(lines)
