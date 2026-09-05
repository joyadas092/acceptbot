from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER

router = Router()

@router.my_chat_member()
async def bot_chat_member_updated(
    event: ChatMemberUpdated,
    bot: Bot,
    chat_repo,
):
    """
    Handle bot's own chat member status changes.
    """
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    chat = event.chat
    added_by = event.from_user

    if new_status in ('administrator', 'creator'):
        # Bot became admin
        # Update or create chat in DB
        chat_data = {
            "id": chat.id,
            "title": chat.title,
            "type": chat.type,
            "admin_id": added_by.id if added_by else None,
            "status": "connected"
        }
        await chat_repo.upsert(chat_data)
        
        has_invite_perm = getattr(event.new_chat_member, "can_invite_users", False)
        
        if added_by:
            try:
                msg = (
                    f"✅ <b>Bot connected to {chat.title}!</b>\n\n"
                    f"Next steps:\n"
                    f"1️⃣ Enable Join Requests in your group/channel settings\n"
                    f"2️⃣ Open /settings to configure approval delay\n"
                    f"3️⃣ Set up your welcome message\n\n"
                )
                if not has_invite_perm:
                    msg += "⚠️ <b>Missing permission:</b> I need <code>can_invite_users</code> to approve join requests!"
                
                await bot.send_message(added_by.id, msg)
            except Exception:
                pass
    
    elif new_status in ('left', 'kicked', 'restricted'):
        if old_status in ('administrator', 'creator', 'member'):
            await chat_repo.update_status(chat.id, "disconnected")
