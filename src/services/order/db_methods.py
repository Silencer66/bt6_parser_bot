from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.common import Order, OrderStatus, User, TradingSession, Group

class DBMethods:
    """DAO для работы с ордерами в базе данных"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        stmt = select(Order).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_session(self, session_id: int) -> List[Order]:
        stmt = select(Order).where(Order.session_id == session_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_order(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_by_id(self, session_id: int) -> Optional[TradingSession]:
        stmt = select(TradingSession).where(TradingSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_group_by_id(self, group_id: int) -> Optional[Group]:
        stmt = select(Group).where(Group.id == group_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
