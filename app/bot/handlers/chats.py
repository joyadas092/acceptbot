from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from ..keyboards.chat_menu import chat_list_keyboard, chat_action_keyboard
from ..filters.is_admin import IsChatAdmin

router = Router()

@router.message(Command('mychannels'))
@router.message(Command('refresh'))
async def my_chats_handler(message: Message, chat_repo):
    """Show list of connected chats."""
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    
    if not chats:
        await message.answer("You don't have any connected chats. Add me as admin to a group or channel to see it here.")
        return
        
    await message.answer(
        "Here are your connected chats. Select one to manage:",
        reply_markup=chat_list_keyboard(chats)
    )

@router.callback_query(F.data == 'menu:chats')
@router.callback_query(F.data == 'menu:chats:refresh')
@router.callback_query(F.data == 'menu:refresh')
async def chats_menu_callback(callback: CallbackQuery, chat_repo):
    """Show chats from main menu. Also handles the Refresh button."""
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)

    if not chats:
        await callback.answer("No connected chats yet.", show_alert=True)
        await callback.message.edit_text(
            "You don't have any connected chats yet.\n"
            "Add me to a group/channel as admin to get started."
        )
        return

    await callback.message.edit_text(
        "Here are your connected chats:",
        reply_markup=chat_list_keyboard(chats)
    )
    await callback.answer()

@router.callback_query(F.data.startswith('chat:select:'))
async def select_chat_callback(callback: CallbackQuery, chat_repo):
    """Show chat detail with action buttons."""
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    
    if not chat:
        return await callback.answer("Chat not found.", show_alert=True)
        
    text = (
        f"💬 <b>{chat.get('title', 'Unknown Chat')}</b>\n\n"
        f"Status: {chat.get('status', 'Unknown')}\n"
        "Select an action to configure:"
    )
    await callback.message.edit_text(text, reply_markup=chat_action_keyboard(chat_id))

@router.callback_query(F.data.startswith('chat:refresh:'))
async def refresh_single_chat(callback: CallbackQuery, chat_repo):
    """Refresh permissions for a single chat."""
    chat_id = int(callback.data.split(':')[2])
    await callback.answer("Chat status refreshed!")
    
    # Reload menu
    chat = await chat_repo.get(chat_id)
    if chat:
        text = f"💬 <b>{chat.get('title', 'Unknown Chat')}</b>\n\nStatus: {chat.get('status', 'Unknown')}\nSelect an action to configure:"
        try:
            await callback.message.edit_text(text, reply_markup=chat_action_keyboard(chat_id))
        except Exception:
            pass  # Suppress "message is not modified" errors

@router.callback_query(F.data.startswith('chat:disconnect:'))
async def disconnect_chat(callback: CallbackQuery, chat_repo):
    """Disconnect a chat."""
    parts = callback.data.split(':')
    if len(parts) > 3 and parts[2] == 'confirm':
        chat_id = int(parts[3])
        await chat_repo.update_status(chat_id, "disconnected")
        await callback.answer("Chat disconnected!")
        
        # Go back to chats list
        user_id = callback.from_user.id
        chats = await chat_repo.get_by_admin(user_id)
        await callback.message.edit_text(
            "Here are your connected chats:",
            reply_markup=chat_list_keyboard(chats)
        )
    else:
        chat_id = int(parts[2])
        # Need keyboard builder for confirm
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        b = InlineKeyboardBuilder()
        b.button(text="⚠️ Confirm Disconnect", callback_data=f"chat:disconnect:confirm:{chat_id}")
        b.button(text="← Cancel", callback_data=f"chat:select:{chat_id}")
        b.adjust(1)
        await callback.message.edit_text("Are you sure you want to disconnect this chat?", reply_markup=b.as_markup())
