from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_keyboard(is_super_admin: bool = False) -> InlineKeyboardMarkup:
    """Main menu shown after /start."""
    builder = InlineKeyboardBuilder()
    
    # Row 1
    builder.button(text="📋 My Chats", callback_data="menu:chats")
    builder.button(text="⚙️ Settings", callback_data="menu:settings")
    # Row 2
    builder.button(text="👋 Welcome", callback_data="menu:welcome")
    builder.button(text="📢 Broadcast", callback_data="menu:broadcast")
    # Row 3
    builder.button(text="📊 Statistics", callback_data="menu:stats")
    builder.button(text="📖 Tutorial", callback_data="menu:tutorial")
    # Row 4
    builder.button(text="💳 Plan", callback_data="menu:plan")
    builder.button(text="❓ Help", callback_data="menu:help")
    # Row 5
    builder.button(text="🔄 Refresh", callback_data="menu:refresh")
    
    builder.adjust(2, 2, 2, 2, 1)
    
    if is_super_admin:
        builder.row(
            builder.button(text="👑 Admin Panel", callback_data="admin:main")
        )
        
    return builder.as_markup()

def welcome_start_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown on /start before any chats connected."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📖 Setup Tutorial", callback_data="tutorial:1")
    builder.button(text="🔄 Refresh Chats", callback_data="menu:refresh")
    builder.button(text="⚙️ Settings", callback_data="menu:settings")
    
    builder.adjust(1)
    return builder.as_markup()
