from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def broadcast_picker_keyboard(chats: list[dict]) -> InlineKeyboardMarkup:
    """Picker for choosing which chat to broadcast to."""
    builder = InlineKeyboardBuilder()
    
    for chat in chats:
        title = chat.get('title', 'Unknown Chat')
        chat_id = chat.get('chat_id')
        builder.button(text=f"📢 {title}", callback_data=f"broadcast:pick:{chat_id}")
        
    builder.button(text="🌐 All Channels", callback_data="broadcast:pick:all")
    builder.adjust(1)
    
    builder.row(
        InlineKeyboardButton(text="← Back", callback_data="menu:main"),
    )
    return builder.as_markup()

def broadcast_confirm_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Confirm or cancel broadcast."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Start Broadcast", callback_data=f"broadcast:confirm:{job_id}")
    builder.button(text="❌ Cancel", callback_data="broadcast:cancel_flow")
    builder.adjust(2)
    return builder.as_markup()

def broadcast_control_keyboard(job_id: str, status: str) -> InlineKeyboardMarkup:
    """Controls for an active broadcast job."""
    builder = InlineKeyboardBuilder()
    
    if status == "running":
        builder.button(text="⏸ Pause", callback_data=f"broadcast:pause:{job_id}")
        builder.button(text="❌ Cancel", callback_data=f"broadcast:cancel:{job_id}")
    elif status == "paused":
        builder.button(text="▶️ Resume", callback_data=f"broadcast:resume:{job_id}")
        builder.button(text="❌ Cancel", callback_data=f"broadcast:cancel:{job_id}")
        
    builder.button(text="🔄 Refresh Status", callback_data=f"broadcast:refresh_status:{job_id}")
    builder.adjust(2, 1)
    return builder.as_markup()
