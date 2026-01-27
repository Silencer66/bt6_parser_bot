from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .db_methods import DBMethods
from src.database.models.common import Group, GroupStatus

class GroupService:
    """Сервис управления группами"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.db_methods = DBMethods(session)

    async def add_group(self, telegram_id: int, title: str, tags: List[str] = None) -> Group:
        """Добавить новую группу"""
        if tags is None:
            tags = []
        
        group = Group(
            telegram_id=telegram_id,
            title=title,
            status=GroupStatus.ACTIVE,
            tags=tags,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_group = await self.db_methods.create_group(group)
        await self.session.commit()
        return new_group

    async def get_group(self, group_id: int) -> Optional[Group]:
        """Получить группу по ID"""
        return await self.db_methods.get_by_id(group_id)

    async def get_group_by_telegram_id(self, telegram_id: int) -> Optional[Group]:
        """Получить группу по Telegram ID"""
        return await self.db_methods.get_by_telegram_id(telegram_id)

    async def list_groups(self, status: Optional[GroupStatus] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Group]:
        """Получить список групп с пагинацией"""
        return await self.db_methods.get_all(status, limit, offset)

    async def get_total_count(self, status: Optional[GroupStatus] = None) -> int:
        """Получить общее количество групп"""
        return await self.db_methods.count_all(status)

    async def get_active_groups(self) -> List[Group]:
        """Получить активные группы"""
        return await self.db_methods.get_all(GroupStatus.ACTIVE)

    async def get_groups_by_tags(self, tags: List[str]) -> List[Group]:
        """Получить группы по тегам"""
        return await self.db_methods.get_by_tags(tags)

    async def update_group_status(self, group_id: int, status: GroupStatus) -> Optional[Group]:
        """Обновить статус группы"""
        group = await self.db_methods.get_by_id(group_id)
        if group:
            group.status = status
            group.updated_at = datetime.utcnow()
            updated = await self.db_methods.update_group(group)
            await self.session.commit()
            return updated
        return None

    async def add_tag_to_group(self, group_id: int, tag: str) -> Optional[Group]:
        """Добавить тег к группе"""
        group = await self.db_methods.get_by_id(group_id)
        if group:
            if tag not in group.tags:
                new_tags = list(group.tags)
                new_tags.append(tag)
                group.tags = new_tags
                group.updated_at = datetime.utcnow()
                updated = await self.db_methods.update_group(group)
                await self.session.commit()
                return updated
        return None

    async def remove_tag_from_group(self, group_id: int, tag: str) -> Optional[Group]:
        """Удалить тег из группы"""
        group = await self.db_methods.get_by_id(group_id)
        if group:
            if tag in group.tags:
                new_tags = [t for t in group.tags if t != tag]
                group.tags = new_tags
                group.updated_at = datetime.utcnow()
                updated = await self.db_methods.update_group(group)
                await self.session.commit()
                return updated
        return None

    async def delete_group(self, group_id: int) -> bool:
        """Удалить группу"""
        result = await self.db_methods.delete_group(group_id)
        if result:
            await self.session.commit()
        return result
