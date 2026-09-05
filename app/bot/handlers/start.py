from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from ..keyboards.main_menu import main_menu_keyboard, welcome_start_keyboard

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, user_repo, chat_repo, is_super_admin: bool):
    """
    1. Register/update user (done via AuthMiddleware)
    2. Show welcome message with main menu keyboard
    3. If user has connected chats: show My Chats summary
    4. If new user: show setup tutorial prompt
    """
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    
    if not chats:
        text = (
            "👋 <b>Welcome to Auto Request Manager!</b>\n\n"
            "I can automatically accept join requests, send welcome messages, "
            "and more for your Telegram groups and channels.\n\n"
            "To get started, please connect your first chat."
        )
        await message.answer(text, reply_markup=welcome_start_keyboard())
    else:
        text = (
            "👋 <b>Welcome back to Auto Request Manager!</b>\n\n"
            f"You have <b>{len(chats)}</b> connected chats.\n"
            "What would you like to do?"
        )
        await message.answer(text, reply_markup=main_menu_keyboard(is_super_admin=is_super_admin))

@router.message(Command('help'))
async def help_handler(message: Message):
    """Show help text with all commands."""
    help_text = (
        "❓ <b>Bot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/tutorial - View the setup tutorial\n"
        "/mychannels - List your connected chats\n"
        "/settings - Bot settings\n"
        "/stats - View statistics\n"
        "/broadcast - Send broadcast message\n"
    )
    await message.answer(help_text)

@router.callback_query(F.data == 'menu:main')
async def main_menu_callback(callback: CallbackQuery, chat_repo, is_super_admin: bool):
    """Return to main menu from any submenu."""
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    
    if not chats:
        text = (
            "👋 <b>Welcome to Auto Request Manager!</b>\n\n"
            "To get started, please connect your first chat."
        )
        await callback.message.edit_text(text, reply_markup=welcome_start_keyboard())
    else:
        text = (
            "👋 <b>Welcome back to Auto Request Manager!</b>\n\n"
            f"You have <b>{len(chats)}</b> connected chats.\n"
            "What would you like to do?"
        )
        await callback.message.edit_text(text, reply_markup=main_menu_keyboard(is_super_admin=is_super_admin))
