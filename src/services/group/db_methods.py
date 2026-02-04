from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.common import Group, GroupStatus

class DBMethods:
    """DAO для работы с группами в базе данных"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_group(self, group: Group) -> Group:
        self.session.add(group)
        await self.session.flush()
        return group

    async def get_by_id(self, group_id: int) -> Optional[Group]:
        stmt = select(Group).where(Group.id == group_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Group]:
        stmt = select(Group).where(Group.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, status: Optional[GroupStatus] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Group]:
        stmt = select(Group)
        if status:
            stmt = stmt.where(Group.status == status)
        
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
            
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self, status: Optional[GroupStatus] = None) -> int:
        from sqlalchemy import func
        stmt = select(func.count(Group.id))
        if status:
            stmt = stmt.where(Group.status == status)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_by_tags(self, tags: List[str]) -> List[Group]:
        stmt = select(Group).where(Group.status == GroupStatus.ACTIVE)
        result = await self.session.execute(stmt)
        all_active = result.scalars().all()
        return [g for g in all_active if any(tag in g.tags for tag in tags)]

    async def update_group(self, group: Group) -> Group:
        self.session.add(group)
        await self.session.flush()
        return group

    async def delete_group(self, group_id: int) -> bool:
        group = await self.get_by_id(group_id)
        if group:
            await self.session.delete(group)
            await self.session.flush()
            return True
        return False

    async def remove_all_groups(self) -> bool:
        stmt = delete(Group)
        await self.session.execute(stmt)
        return True
