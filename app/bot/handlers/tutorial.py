from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

TUTORIAL_SECTIONS = {
    '1': {
        'title': '📱 How to Add the Bot',
        'text': '''<b>1. Adding the Bot</b>

1. Open your Telegram group or channel
2. Go to Group Info → Administrators
3. Tap "Add Administrator"
4. Search for @YourBotUsername
5. Enable these permissions:
   ✅ Invite Users via Link (required)
   ✅ Add Admins (optional, for notifications)
6. Tap Save'''
    },
    '2': {
        'title': '🔑 Required Permissions',
        'text': '''<b>2. Permissions Explained</b>

The bot <b>must</b> have the <code>Invite Users via Link</code> permission. 
Without this, it cannot approve join requests.

If you want the bot to notify you of issues, also grant <code>Add Admins</code> so it can message you about admin status changes.'''
    },
    '3': {
        'title': '🔗 Enable Join Requests',
        'text': '''<b>3. Enabling Join Requests</b>

For the bot to work, your chat needs to have Join Requests turned on.

Go to: Group/Channel Info → Edit → Invite Links → <b>Approve New Members</b> ON

Only users joining through an invite link with this setting ON will generate a join request.'''
    },
    '4': {
        'title': '⚡ Configure Auto Approval',
        'text': '''<b>4. Auto Approval Settings</b>

You can set the bot to approve requests:
- Immediately
- After a delay (e.g. 5m, 1h)

Use the ⚡ Approval button in the chat menu to configure this.'''
    },
    '5': {
        'title': '👋 Configure Welcome Messages',
        'text': '''<b>5. Welcome Messages</b>

You can configure the bot to send a welcome DM to users.

Triggers:
- On Request: When they ask to join
- On Approval: Immediately after approval
- Delayed: Sometime after approval'''
    },
    '6': {
        'title': '🔘 Add Buttons to Welcome',
        'text': '''<b>6. Inline Buttons</b>

You can add interactive URL buttons to your welcome message to direct users to other channels, websites, or rules.

Use the 🔘 Buttons menu to add and organize them.'''
    },
    '7': {
        'title': '📢 Broadcast System',
        'text': '''<b>7. Broadcasts</b>

Use the 📢 Broadcast menu to send a message to all users who have interacted with the bot through your channels.

Note: Telegram limits how fast messages can be sent.'''
    },
    '8': {
        'title': '🔧 Troubleshooting',
        'text': '''<b>8. Troubleshooting</b>

❓ <b>Bot is admin but not accepting requests</b>
→ Check that Join Requests are ENABLED in your group settings
→ Check bot has <code>can_invite_users</code> permission

❓ <b>Bot doesn't appear in Refresh</b>
→ Remove and re-add the bot as admin
→ Make sure you pressed /start in the bot

❓ <b>Welcome message isn't delivered</b>
→ Telegram limits messaging users before they join
→ This is normal — message delivers after approval

❓ <b>Admin didn't receive notification</b>
→ You must /start the bot before it can message you

❓ <b>Broadcast says users unavailable</b>
→ Users may have blocked the bot
→ This is counted as a failed delivery, not an error'''
    }
}

def get_tutorial_keyboard(section: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    current = int(section)
    total = len(TUTORIAL_SECTIONS)
    
    row = []
    if current > 1:
        row.append(builder.button(text="← Previous", callback_data=f"tutorial:{current-1}"))
        
    row.append(builder.button(text=f"Section {current}/{total}", callback_data="ignore"))
    
    if current < total:
        row.append(builder.button(text="Next →", callback_data=f"tutorial:{current+1}"))
        
    builder.adjust(len(row))
    builder.row(builder.button(text="← Exit Tutorial", callback_data="menu:main"))
    return builder

@router.message(Command('tutorial'))
async def tutorial_start(message: Message):
    """Show tutorial section 1 with navigation."""
    section = '1'
    data = TUTORIAL_SECTIONS[section]
    text = f"{data['title']}\n\n{data['text']}"
    await message.answer(text, reply_markup=get_tutorial_keyboard(section).as_markup())

@router.callback_query(F.data.startswith('tutorial:'))
async def tutorial_navigate(callback: CallbackQuery):
    """Navigate between tutorial sections."""
    section = callback.data.split(':')[1]
    if section not in TUTORIAL_SECTIONS:
        return await callback.answer("Section not found.")
        
    data = TUTORIAL_SECTIONS[section]
    text = f"{data['title']}\n\n{data['text']}"
    await callback.message.edit_text(text, reply_markup=get_tutorial_keyboard(section).as_markup())
