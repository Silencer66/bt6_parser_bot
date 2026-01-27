from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .db_methods import DBMethods
from src.database.models.common import (
    TradingSession, 
    TradeDirection, 
    PaymentMethod, 
    SessionStatus
)

class SessionService:
    """Сервис управления торговыми сессиями"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.db_methods = DBMethods(session)

    async def create_session(
        self,
        direction: TradeDirection,
        currency_from: str,
        currency_to: str,
        volume: float,
        payment_method: Optional[PaymentMethod] = None,
        time_to_live_minutes: int = 60,
        target_tags: List[str] = None
    ) -> TradingSession:
        """Создать новую торговую сессию"""
        if target_tags is None:
            target_tags = []

        session_obj = TradingSession(
            direction=direction,
            currency_from=currency_from,
            currency_to=currency_to,
            volume=volume,
            payment_method=payment_method,
            time_to_live_minutes=time_to_live_minutes,
            status=SessionStatus.CREATED,
            created_at=datetime.utcnow(),
            target_tags=target_tags
        )
        
        new_session = await self.db_methods.create_session(session_obj)
        await self.session.commit()
        return new_session

    async def get_session(self, session_id: int) -> Optional[TradingSession]:
        """Получить сессию по ID"""
        return await self.db_methods.get_session_by_id(session_id)

    async def get_active_sessions(self) -> List[TradingSession]:
        """Получить активные сессии"""
        return await self.db_methods.get_active_sessions()

    async def activate_session(self, session_id: int) -> Optional[TradingSession]:
        """Активировать сессию"""
        session_obj = await self.db_methods.get_session_by_id(session_id)
        if session_obj:
            session_obj.status = SessionStatus.ACTIVE
            updated = await self.db_methods.update_session(session_obj)
            await self.session.commit()
            return updated
        return None

    async def complete_session(self, session_id: int) -> Optional[TradingSession]:
        """Завершить сессию"""
        session_obj = await self.db_methods.get_session_by_id(session_id)
        if session_obj:
            session_obj.status = SessionStatus.COMPLETED
            updated = await self.db_methods.update_session(session_obj)
            await self.session.commit()
            return updated
        return None

    async def get_target_groups(self, trading_session: TradingSession) -> List:
        """Получить целевые группы для рассылки"""
        return await self.db_methods.get_groups_by_tags(trading_session.target_tags)

    async def check_expired_sessions(self) -> List[TradingSession]:
        """Проверить и завершить истекшие сессии"""
        active_sessions = await self.get_active_sessions()
        expired = []
        
        for session_obj in active_sessions:
            if session_obj.is_expired():
                session_obj.status = SessionStatus.EXPIRED
                await self.db_methods.update_session(session_obj)
                expired.append(session_obj)
        
        if expired:
            await self.session.commit()
        
        return expired
