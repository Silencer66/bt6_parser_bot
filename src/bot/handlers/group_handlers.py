"""
Обработчики для управления группами
"""
from typing import List, Optional, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from services import GroupService
from database import GroupStatus

router = Router()

GROUPS_PER_PAGE = 10

async def get_groups_page_data(session: AsyncSession, page: int = 1):
    """Подготовка текста и клавиатуры для страницы групп"""
    service = GroupService(session)
    total_count = await service.get_total_count()
    
    if total_count == 0:
        return "📋 Список групп пуст. Группы добавляются через Userbot.", None

    total_pages = (total_count + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * GROUPS_PER_PAGE
    
    groups = await service.list_groups(limit=GROUPS_PER_PAGE, offset=offset)
    
    text = f"📋 <b>Список отслеживаемых групп (Страница {page}/{total_pages}):</b>\n\n"
    for idx, group in enumerate(groups, offset + 1):
        status_icon = "🔊" if group.status == GroupStatus.ACTIVE else "🔇"
        tags_text = ", ".join(group.tags) if group.tags else "нет тегов"
        text += f"{idx}. {status_icon} <b>{group.title}</b>\n"
        text += f"   ID: <code>{group.telegram_id}</code>\n"
        text += f"   Теги: {tags_text}\n\n"

    buttons = []
    for idx, group in enumerate(groups, offset + 1):
        # Обрезаем длинные названия для кнопок
        display_title = (group.title[:25] + '..') if len(group.title) > 25 else group.title
        
        # Статус кнопка
        status_text = "🔊 Включить" if group.status == GroupStatus.INACTIVE else "🔇 Выключить"
        status_action = "enable_group" if group.status == GroupStatus.INACTIVE else "disable_group"

        buttons.append([
            InlineKeyboardButton(text=f"{idx}. {display_title}", callback_data=f"groups_page:{page}"), # Просто кнопка-метка
            InlineKeyboardButton(text=status_text, callback_data=f"{status_action}:{group.id}:{page}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_group:{group.id}:{page}")
        ])

    # Кнопки навигации
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"groups_page:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"groups_page:{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
        
    # Кнопка синхронизации и обновления
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"groups_page:{page}"),
        InlineKeyboardButton(text="📥 Синхронизировать", callback_data="sync_groups")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


@router.message(Command("groups"))
async def cmd_groups(message: Message, session: AsyncSession):
    """Список групп"""
    text, keyboard = await get_groups_page_data(session, page=1)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("sync"))
async def cmd_sync(message: Message, session: AsyncSession, userbot: Any):
    """Принудительная синхронизация групп"""
    from userbot.handlers import sync_groups
    sent_msg = await message.answer("🔍 Синхронизация... это может занять время.")
    await sync_groups(userbot.client)
    await sent_msg.edit_text("✅ Синхронизация завершена!")
    # Показываем обновленный список
    text, keyboard = await get_groups_page_data(session, page=1)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "sync_groups")
async def callback_sync_groups(callback: CallbackQuery, session: AsyncSession, userbot: Any):
    """Синхронизация через кнопку"""
    from userbot.handlers import sync_groups
    await callback.answer("⏳ Начинаю сканирование чатов...")
    await sync_groups(userbot.client)
    await callback.message.answer("✅ Группы синхронизированы!")
    
    # Обновляем сообщение со списком
    text, keyboard = await get_groups_page_data(session, page=1)
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("groups_page:"))
async def callback_groups_page(callback: CallbackQuery, session: AsyncSession):
    """Переключение страниц списка групп или обновление текущей"""
    page = int(callback.data.split(":")[1])
    text, keyboard = await get_groups_page_data(session, page=page)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("delete_group:"))
async def callback_delete_group(callback: CallbackQuery, session: AsyncSession):
    """Удаление группы из базы"""
    parts = callback.data.split(":")
    group_id = int(parts[1])
    current_page = int(parts[2])
    
    service = GroupService(session)
    success = await service.delete_group(group_id)
    
    if success:
        await callback.answer("✅ Группа удалена")
        # Обновляем текущую страницу
        text, keyboard = await get_groups_page_data(session, page=current_page)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            # Если страница стала пустой или текст не поменялся
            pass
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data == "refresh_groups")
async def callback_refresh_groups(callback: CallbackQuery, session: AsyncSession):
    """Устаревший хендлер обновления (для совместимости)"""
    text, keyboard = await get_groups_page_data(session, page=1)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("Список обновлен")


@router.callback_query(F.data.startswith("enable_group:"))
async def callback_enable_group(callback: CallbackQuery, session: AsyncSession):
    """Включение группы (unmute)"""
    parts = callback.data.split(":")
    group_id = int(parts[1])
    current_page = int(parts[2])
    
    service = GroupService(session)
    await service.update_group_status(group_id, GroupStatus.ACTIVE)
    
    await callback.answer("✅ Группа включена")
    text, keyboard = await get_groups_page_data(session, page=current_page)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass


@router.callback_query(F.data.startswith("disable_group:"))
async def callback_disable_group(callback: CallbackQuery, session: AsyncSession):
    """Выключение группы (mute)"""
    parts = callback.data.split(":")
    group_id = int(parts[1])
    current_page = int(parts[2])
    
    service = GroupService(session)
    await service.update_group_status(group_id, GroupStatus.INACTIVE)
    
    await callback.answer("🔇 Группа выключена")
    text, keyboard = await get_groups_page_data(session, page=current_page)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass
