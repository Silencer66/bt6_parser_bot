"""
Обработчики для управления группами
"""
from typing import List, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.services import GroupService
from src.database import GroupStatus

router = Router()


class AddGroupStates(StatesGroup):
    waiting_for_forward = State()


@router.message(Command("groups"))
async def cmd_groups(message: Message, session: AsyncSession):
    """Список групп"""
    service = GroupService(session)
    groups = await service.list_groups()
    
    if not groups:
        await message.answer("📋 Список групп пуст. Используйте /add_group для добавления.")
        return

    text = "📋 **Список групп:**\n\n"
    for idx, group in enumerate(groups, 1):
        status_icon = "✅" if group.status == GroupStatus.ACTIVE else "⏸️"
        tags_text = ", ".join(group.tags) if group.tags else "нет тегов"
        text += f"{idx}. {status_icon} {group.title}\n"
        text += f"   ID: {group.telegram_id} | Теги: {tags_text}\n\n"

    # Кнопки для управления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить группу", callback_data="add_group")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_groups")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("add_group"))
async def cmd_add_group(message: Message, state: FSMContext):
    """Начать процесс добавления группы"""
    await message.answer(
        "📤 Перешлите любое сообщение из группы, которую хотите добавить.\n"
        "Бот автоматически определит ID группы."
    )
    await state.set_state(AddGroupStates.waiting_for_forward)


@router.message(AddGroupStates.waiting_for_forward, F.forward_from_chat)
async def process_forwarded_message(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка пересланного сообщения"""
    chat = message.forward_from_chat
    
    if chat.type != "supergroup" and chat.type != "group":
        await message.answer("❌ Это не группа. Перешлите сообщение из группы.")
        return

    service = GroupService(session)
    
    # Проверяем, не добавлена ли уже группа
    existing = await service.get_group_by_telegram_id(chat.id)
    if existing:
        await message.answer(f"⚠️ Группа '{chat.title}' уже добавлена.")
        await state.clear()
        return

    # Добавляем группу
    group = await service.add_group(
        telegram_id=chat.id,
        title=chat.title or f"Group {chat.id}",
        tags=[]
    )

    await message.answer(
        f"✅ Группа '{group.title}' успешно добавлена!\n"
        f"ID: {group.telegram_id}\n\n"
        f"Используйте /edit_group для добавления тегов."
    )
    await state.clear()


@router.callback_query(F.data == "refresh_groups")
async def callback_refresh_groups(callback: CallbackQuery, session: AsyncSession):
    """Обновить список групп"""
    await callback.answer()
    service = GroupService(session)
    groups = await service.list_groups()
    
    if not groups:
        await callback.message.edit_text("📋 Список групп пуст.")
        return

    text = "📋 **Список групп:**\n\n"
    for idx, group in enumerate(groups, 1):
        status_icon = "✅" if group.status == GroupStatus.ACTIVE else "⏸️"
        tags_text = ", ".join(group.tags) if group.tags else "нет тегов"
        text += f"{idx}. {status_icon} {group.title}\n"
        text += f"   ID: {group.telegram_id} | Теги: {tags_text}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить группу", callback_data="add_group")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_groups")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
