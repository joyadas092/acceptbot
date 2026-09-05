from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from ..keyboards.chat_menu import chat_list_keyboard, chat_action_keyboard
from app.core.logging import get_logger

router = Router()
logger = get_logger('settings')


@router.message(Command('settings'))
async def settings_command(message: Message, chat_repo):
    """Show settings for all connected chats or prompt to select one."""
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    logger.info("settings_command", user_id=user_id, chat_count=len(chats),
                chat_ids=[c.get('chat_id') for c in chats])

    if not chats:
        await message.answer("You don't have any connected chats. Please add the bot to a chat first.")
        return

    await message.answer(
        "Select a chat to view its settings:",
        reply_markup=chat_list_keyboard(chats)
    )

@router.callback_query(F.data == 'menu:settings')
async def settings_menu(callback: CallbackQuery, chat_repo):
    """Settings from main menu."""
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    
    if not chats:
        await callback.answer("You don't have any connected chats.", show_alert=True)
        return
        
    await callback.message.edit_text(
        "Select a chat to view its settings:",
        reply_markup=chat_list_keyboard(chats)
    )

@router.callback_query(F.data.startswith('settings:chat:'))
async def chat_settings_menu(callback: CallbackQuery, chat_repo):
    """Show settings for a specific chat with all options."""
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.")
        
    text = f"⚙️ <b>Settings for {chat.get('title')}</b>\nChoose a category:"
    await callback.message.edit_text(text, reply_markup=chat_action_keyboard(chat_id))
