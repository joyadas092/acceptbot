from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery

class CallbackOwner(BaseFilter):
    """
    Verifies that the user pressing a callback button is the
    same user who received the message.
    Prevents other users from pressing another user's buttons.
    """
    async def __call__(self, callback: CallbackQuery) -> bool:
        if not callback.message or not callback.message.chat:
            return True # Not attached to a message
            
        # In a private chat, it's always the owner.
        if callback.message.chat.type == "private":
            return True
            
        # If it's in a group/channel and there's a reply to a user message, check it
        if callback.message.reply_to_message:
            owner_id = callback.message.reply_to_message.from_user.id
            if callback.from_user.id != owner_id:
                await callback.answer('This is not your menu.', show_alert=True)
                return False
        
        # Optionally support encoded owner_id in callback data prefix if applicable
        # This implementation assumes basic usage where buttons in private chats are the main use case.
        return True
