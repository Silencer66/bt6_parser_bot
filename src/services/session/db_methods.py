from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.common import TradingSession, Group, GroupStatus

class DBMethods:
    """DAO для работы с сессиями в базе данных"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, session_obj: TradingSession) -> TradingSession:
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_session_by_id(self, session_id: int) -> Optional[TradingSession]:
        stmt = select(TradingSession).where(TradingSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_sessions(self) -> List[TradingSession]:
        stmt = select(TradingSession).where(TradingSession.status == SessionStatus.ACTIVE)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_session(self, session_obj: TradingSession) -> TradingSession:
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_groups_by_tags(self, tags: List[str]) -> List[Group]:
        if not tags:
            stmt = select(Group).where(Group.status == GroupStatus.ACTIVE)
        else:
            # PostgreSQL specific: check if ANY of the tags in list are in the JSON array
            # For simplicity, we filter in Python or use a basic contains check if JSON is used
            # Here we assume a simple overlap check
            stmt = select(Group).where(Group.status == GroupStatus.ACTIVE)
            result = await self.session.execute(stmt)
            all_active = result.scalars().all()
            return [g for g in all_active if any(tag in g.tags for tag in tags)]
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
