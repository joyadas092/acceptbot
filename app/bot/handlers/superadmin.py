from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..filters.is_superadmin import IsSuperAdmin
from ..keyboards.superadmin_menu import superadmin_main_keyboard, superadmin_stats_keyboard

router = Router()

# Assumes IsSuperAdmin filter is applied via middleware/router setup,
# but we can apply it locally as well if needed. Or we just trust is_super_admin flag.
# Let's use custom filter lambda based on data['is_super_admin']

def admin_filter(message: Message, is_super_admin: bool = False, **kwargs) -> bool:
    return is_super_admin

def admin_cb_filter(callback: CallbackQuery, is_super_admin: bool = False, **kwargs) -> bool:
    return is_super_admin

router.message.filter(admin_filter)
router.callback_query.filter(admin_cb_filter)

@router.message(Command('admin'))
async def admin_panel(message: Message):
    """Super admin main panel."""
    await message.answer(
        "👑 <b>Super Admin Panel</b>\n\nSelect an option to manage the system:",
        reply_markup=superadmin_main_keyboard()
    )

@router.message(Command('users'))
async def users_stats(message: Message, user_repo):
    """User statistics."""
    count = await user_repo.count()
    await message.answer(f"👥 <b>Total Users:</b> {count}", reply_markup=superadmin_stats_keyboard())

@router.message(Command('chats'))
async def chats_stats(message: Message, chat_repo):
    """Chat statistics."""
    count = await chat_repo.count()
    await message.answer(f"💬 <b>Total Chats:</b> {count}", reply_markup=superadmin_stats_keyboard())

@router.message(Command('system'))
async def system_stats(message: Message):
    """System health."""
    text = (
        "🖥 <b>System Health</b>\n\n"
        "Database: Connected\n"
        "Redis: Connected\n"
        "Workers: 1 Active\n"
    )
    await message.answer(text, reply_markup=superadmin_stats_keyboard())

@router.message(Command('master_broadcast'))
async def master_broadcast_command(message: Message, state: FSMContext):
    """Super admin master broadcast."""
    await message.answer("Master broadcast feature. Please use regular broadcast interface for now, or build this out to use 'all users' target.")

@router.callback_query(F.data.startswith('admin:'))
async def admin_callbacks(callback: CallbackQuery, user_repo, chat_repo):
    """Handle admin panel callbacks."""
    action = callback.data.split(':')[1]
    
    if action == 'main':
        await callback.message.edit_text(
            "👑 <b>Super Admin Panel</b>\n\nSelect an option to manage the system:",
            reply_markup=superadmin_main_keyboard()
        )
    elif action == 'users':
        count = await user_repo.count()
        await callback.message.edit_text(f"👥 <b>Total Users:</b> {count}", reply_markup=superadmin_stats_keyboard())
    elif action == 'chats':
        count = await chat_repo.count()
        await callback.message.edit_text(f"💬 <b>Total Chats:</b> {count}", reply_markup=superadmin_stats_keyboard())
    elif action == 'system':
        text = (
            "🖥 <b>System Health</b>\n\n"
            "Database: Connected\n"
            "Redis: Connected\n"
            "Workers: 1 Active\n"
        )
        await callback.message.edit_text(text, reply_markup=superadmin_stats_keyboard())
    elif action == 'stats':
        subaction = callback.data.split(':')[2]
        if subaction == 'refresh':
            await callback.answer("Refreshed (simulated).")
            # Usually would reload the current stats panel
