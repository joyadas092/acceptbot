from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def broadcast_target_keyboard(chat_id: int | None, chats: list[dict]) -> InlineKeyboardMarkup:
    """Choose broadcast target."""
    builder = InlineKeyboardBuilder()
    
    if chat_id:
        builder.button(text="📢 This Channel", callback_data=f"broadcast:target:chat:{chat_id}")
        
    builder.button(text="🌐 All My Channels", callback_data="broadcast:target:all")
    
    builder.adjust(1)
    builder.row(builder.button(text="← Back", callback_data="broadcast:cancel_flow"))
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
