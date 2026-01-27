from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .db_methods import DBMethods
from src.database.models.common import Order, OrderStatus, TradeDirection

class OrderService:
    """Сервис для работы с ордерами"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.db_methods = DBMethods(session)

    async def create_order(
        self,
        session_id: int,
        group_id: int,
        user_id: int,
        username: str,
        side: TradeDirection,
        price: float,
        volume: float,
        currency: str,
        message_id: Optional[int] = None,
        raw_message: str = ""
    ) -> Order:
        """Создать новый ордер"""
        # Проверяем пользователя
        user_obj = await self.db_methods.get_user_by_telegram_id(user_id)
        if user_obj and user_obj.is_blacklisted:
            raise ValueError("Пользователь в черном списке")

        order_obj = Order(
            session_id=session_id,
            group_id=group_id,
            user_id=user_id,
            username=username,
            side=side,
            price=price,
            volume=volume,
            currency=currency,
            status=OrderStatus.PENDING,
            message_id=message_id,
            raw_message=raw_message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        if not order_obj.is_valid():
            raise ValueError("Ордер невалиден")

        new_order = await self.db_methods.create_order(order_obj)
        await self.session.commit()
        return new_order

    async def get_order(self, order_id: int) -> Optional[Order]:
        """Получить ордер по ID"""
        return await self.db_methods.get_by_id(order_id)

    async def get_orders_by_session(self, session_id: int) -> List[Order]:
        """Получить все ордера сессии"""
        return await self.db_methods.get_by_session(session_id)

    async def accept_order(self, order_id: int) -> Optional[Order]:
        """Принять ордер"""
        order_obj = await self.db_methods.get_by_id(order_id)
        if order_obj:
            order_obj.status = OrderStatus.ACCEPTED
            order_obj.updated_at = datetime.utcnow()
            updated = await self.db_methods.update_order(order_obj)
            await self.session.commit()
            return updated
        return None

    async def reject_order(self, order_id: int) -> Optional[Order]:
        """Отклонить ордер"""
        order_obj = await self.db_methods.get_by_id(order_id)
        if order_obj:
            order_obj.status = OrderStatus.REJECTED
            order_obj.updated_at = datetime.utcnow()
            updated = await self.db_methods.update_order(order_obj)
            await self.session.commit()
            return updated
        return None
