from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ..keyboards.settings_menu import approval_settings_keyboard

class ApprovalStates(StatesGroup):
    waiting_custom_delay = State()

router = Router()

@router.callback_query(F.data == 'menu:approval')
async def approval_menu_callback(callback: CallbackQuery, chat_repo):
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    if not chats:
        return await callback.answer("You don't have any connected chats.", show_alert=True)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for c in chats:
        c_id = c.get('chat_id')
        title = c.get('title', 'Chat')
        b.button(text=f"⚡ {title}", callback_data=f"settings:approval:{c_id}")
    b.button(text="← Back", callback_data="menu:main")
    b.adjust(1)
    
    await callback.message.edit_text(
        "⚡ <b>Approval Settings</b>\n\nSelect a chat to configure its approval settings:",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith('settings:approval:'))
async def approval_settings_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.")

    # approval_settings lives on the chat doc; captcha_enabled lives on chat_settings.
    approval_settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    full_settings = await chat_repo.get_chat_settings_with_defaults(chat_id)
    captcha_enabled = bool(full_settings.get('captcha_enabled', False))

    await callback.message.edit_text(
        "⚡ <b>Approval Settings</b>\n\nConfigure how join requests are handled.",
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=approval_settings.get('enabled', True),
            delay_seconds=approval_settings.get('delay', 0),
            captcha_enabled=captcha_enabled,
        )
    )


@router.callback_query(F.data.startswith('captcha:toggle:'))
async def toggle_captcha(callback: CallbackQuery, chat_repo):
    """Toggle captcha mode for the chat. Only chat admins can use this button."""
    chat_id = int(callback.data.split(':')[2])

    # Admin gate — fetch chat's admin list, verify caller is one
    try:
        member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
        if member.status not in ('creator', 'administrator'):
            return await callback.answer("Only chat admins can change this.", show_alert=True)
    except Exception:
        return await callback.answer("Couldn't verify admin status.", show_alert=True)

    current = await chat_repo.get_chat_settings_with_defaults(chat_id)
    new_value = not bool(current.get('captcha_enabled', False))
    await chat_repo.upsert_settings(chat_id, {'captcha_enabled': new_value})

    # Refresh keyboard with new state
    chat = await chat_repo.get(chat_id)
    approval_settings = (chat or {}).get('approval_settings', {'enabled': True, 'delay': 0})
    await callback.message.edit_reply_markup(
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=approval_settings.get('enabled', True),
            delay_seconds=approval_settings.get('delay', 0),
            captcha_enabled=new_value,
        )
    )
    await callback.answer(
        f"Captcha {'enabled' if new_value else 'disabled'} ✅"
    )


@router.message(Command('captcha'))
async def captcha_command(message: Message, chat_repo):
    """
    Admin command to toggle captcha in the current chat.
    Usage (in the chat itself, as admin):  /captcha on   |   /captcha off
    Or in private chat:  /captcha <chat_id> on|off
    """
    args = (message.text or '').split()
    target_chat_id: int
    desired: bool | None

    if len(args) == 2 and args[1] in ('on', 'off'):
        # In-chat usage
        target_chat_id = message.chat.id
        desired = args[1] == 'on'
    elif len(args) == 3 and args[2] in ('on', 'off'):
        # Private usage: /captcha <chat_id> on|off
        try:
            target_chat_id = int(args[1])
        except ValueError:
            return await message.answer("Invalid chat id.")
        desired = args[2] == 'on'
    else:
        return await message.answer(
            "Usage:\n"
            "• In the chat: <code>/captcha on</code> or <code>/captcha off</code>\n"
            "• In private:  <code>/captcha &lt;chat_id&gt; on|off</code>"
        )

    # Admin check
    try:
        member = await message.bot.get_chat_member(target_chat_id, message.from_user.id)
        if member.status not in ('creator', 'administrator'):
            return await message.answer("Only chat admins can change this.")
    except Exception as e:
        return await message.answer(f"Couldn't verify admin status: {e}")

    await chat_repo.upsert_settings(target_chat_id, {'captcha_enabled': bool(desired)})
    state = 'enabled' if desired else 'disabled'
    await message.answer(f"🛡 Captcha {state} for chat <code>{target_chat_id}</code>.")

@router.callback_query(F.data.startswith('approval:toggle:'))
async def toggle_auto_approval(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    
    settings['enabled'] = not settings['enabled']
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=settings['delay']
        )
    )

@router.callback_query(F.data.startswith('approval:delay:'))
async def set_approval_delay(callback: CallbackQuery, chat_repo, state: FSMContext):
    parts = callback.data.split(':')
    chat_id = int(parts[2])
    val = parts[3]
    
    if val == 'custom':
        await state.set_state(ApprovalStates.waiting_custom_delay)
        await state.update_data(chat_id=chat_id)
        await callback.message.answer("Enter custom delay in minutes (e.g. 10):")
        await callback.answer()
        return
        
    delay_seconds = int(val)
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    settings['delay'] = delay_seconds
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=delay_seconds
        )
    )

@router.message(ApprovalStates.waiting_custom_delay)
async def receive_custom_delay(message: Message, state: FSMContext, chat_repo):
    if not message.text or not message.text.isdigit():
        return await message.answer("Please enter a valid number of minutes.")
        
    minutes = int(message.text)
    delay_seconds = minutes * 60
    
    data = await state.get_data()
    chat_id = data['chat_id']
    
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    settings['delay'] = delay_seconds
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await state.clear()
    
    await message.answer(
        f"✅ Custom delay set to {minutes} minutes.",
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=delay_seconds
        )
    )
