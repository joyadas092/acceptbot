from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

class IsChatAdmin(BaseFilter):
    """
    Filter that checks if the current user is admin of the chat.
    Used for chat-specific commands.
    Verifies via Telegram API (not just DB).
    """
    async def __call__(self, event: Message | CallbackQuery, bot: Bot, **kwargs) -> bool:
        user_id = event.from_user.id
        
        chat_id = None
        if isinstance(event, CallbackQuery) and ":" in event.data:
            # Try to extract chat_id from callback data if it has one
            parts = event.data.split(':')
            for part in parts:
                if part.lstrip('-').isdigit() and len(part) > 6:
                    chat_id = int(part)
                    break
        
        if not chat_id and isinstance(event, Message) and event.chat.type != 'private':
            chat_id = event.chat.id
            
        if not chat_id:
            # Can't determine chat, assume fail or fallback to true if not applicable
            return False
            
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ('administrator', 'creator'):
                return True
        except Exception:
            pass
            
        if isinstance(event, CallbackQuery):
            await event.answer("You are not an admin of this chat.", show_alert=True)
            
        return False
