from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from ..keyboards.settings_menu import welcome_settings_keyboard
from ..keyboards.chat_menu import welcome_chat_picker_keyboard

router = Router()

# FSM states for the welcome editor. The state machine intentionally has
# just two phases: "in the menu" (no state) and "collecting media or text".
# All edits are saved immediately so a refresh never loses work.
class WelcomeStates(StatesGroup):
    editing_text = State()
    waiting_media = State()


# --------------------------------------------------------------------------- #
# /welcome — entry point. Always starts by asking which chat to configure.
# --------------------------------------------------------------------------- #
@router.message(Command('welcome'))
async def welcome_command(message: Message, chat_repo):
    """Entry: show chat picker. If 1 chat, jump straight to editor."""
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    if not chats:
        return await message.answer(
            "You don't have any connected chats yet.\n"
            "Add me to a group or channel first via /start."
        )
    if len(chats) == 1:
        chat = chats[0]
        return await _show_welcome_editor(message, chat_repo, chat['chat_id'])
    await message.answer(
        "👋 <b>Welcome Message Setup</b>\n\n"
        "Select the group or channel you want to configure the welcome "
        "message for:",
        reply_markup=welcome_chat_picker_keyboard(chats),
    )


@router.callback_query(F.data == 'menu:welcome')
async def welcome_menu_callback(callback: CallbackQuery, chat_repo):
    """Same picker, reached from the main-menu '👋 Welcome' button."""
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    if not chats:
        return await callback.answer("No connected chats.", show_alert=True)
    if len(chats) == 1:
        chat = chats[0]
        return await _show_welcome_editor(
            callback.message, chat_repo, chat['chat_id'], edit=True, bot=callback.bot
        )
    await callback.message.edit_text(
        "👋 <b>Welcome Message Setup</b>\n\n"
        "Select the group or channel you want to configure:",
        reply_markup=welcome_chat_picker_keyboard(chats),
    )
    await callback.answer()


# --------------------------------------------------------------------------- #
# Chat picked → show the editor keyboard.
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('welcome:pick:'))
async def welcome_pick_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    await _show_welcome_editor(
        callback.message, chat_repo, chat_id, edit=True, bot=callback.bot
    )
    await callback.answer()


# --------------------------------------------------------------------------- #
# Editor keyboard (also reachable from chat_action_keyboard via
# settings:welcome:<chat_id> for parity with the old flow).
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('settings:welcome:'))
async def welcome_settings_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    await _show_welcome_editor(
        callback.message, chat_repo, chat_id, edit=True, bot=callback.bot
    )
    await callback.answer()


async def _show_welcome_editor(target, chat_repo, chat_id, *, edit=False, bot=None):
    """Render the editor. `target` is a Message; `edit` switches edit_text vs answer."""
    chat = await chat_repo.get(chat_id)
    if not chat:
        text = "Chat not found."
        if edit:
            return await target.edit_text(text)
        return await target.answer(text)

    welcome = chat.get('welcome_settings', {}) or {}
    # Buttons live in the chat_settings doc (legacy field); the editor and
    # the renderer both read them from there. We pull both sources so the
    # "✅" indicator reflects what the admin has actually configured.
    settings_doc = await chat_repo.get_chat_settings(chat_id) or {}
    buttons = settings_doc.get('welcome_buttons', []) or chat.get('welcome_buttons', []) or []
    has_text = bool(welcome.get('text'))
    has_media = bool(welcome.get('media_file_id'))
    has_buttons = bool(buttons)

    title = chat.get('title', 'this chat')
    body = (
        f"👋 <b>Welcome Editor — {title}</b>\n\n"
        "Configure what newly approved members receive.\n"
        "✅ marks what's already set.\n\n"
        "Tip: text supports <b>bold</b>, <i>italic</i>, <code>code</code>, "
        "links, and premium emoji "
        '(<code>&lt;tg-emoji emoji-id="12345"&gt;⭐&lt;/tg-emoji&gt;</code>).'
    )
    markup = welcome_settings_keyboard(
        chat_id=chat_id,
        has_text=has_text,
        has_media=has_media,
        has_buttons=has_buttons,
    )
    if edit:
        return await target.edit_text(body, reply_markup=markup)
    return await target.answer(body, reply_markup=markup)


# --------------------------------------------------------------------------- #
# Edit text
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('welcome:edit_text:'))
async def start_edit_welcome_text(callback: CallbackQuery, state: FSMContext, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    current = (chat.get('welcome_settings') or {}).get('text', '')

    await state.set_state(WelcomeStates.editing_text)
    await state.update_data(chat_id=chat_id)

    snippet = current[:200] + ('…' if len(current) > 200 else '') if current else '(empty)'
    await callback.message.answer(
        "✏️ <b>Send the new welcome message text.</b>\n\n"
        "<b>Formatting supported:</b>\n"
        "• <code>&lt;b&gt;bold&lt;/b&gt;</code>, <code>&lt;i&gt;italic&lt;/i&gt;</code>, "
        "<code>&lt;u&gt;underline&lt;/u&gt;</code>, <code>&lt;s&gt;strike&lt;/s&gt;</code>\n"
        "• <code>&lt;code&gt;monospace&lt;/code&gt;</code>\n"
        "• Links: <code>&lt;a href=\"https://example.com\"&gt;text&lt;/a&gt;</code>\n"
        "• Premium emoji: "
        '<code>&lt;tg-emoji emoji-id="5368324170671202286"&gt;⭐&lt;/tg-emoji&gt;</code>\n\n'
        f"<b>Current:</b>\n{snippet}\n\n"
        "Send /cancel to abort."
    )
    await callback.answer()


@router.message(WelcomeStates.editing_text, Command('cancel'))
async def cancel_edit_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Edit cancelled.")


@router.message(WelcomeStates.editing_text)
async def receive_welcome_text(message: Message, state: FSMContext, chat_repo):
    # Allow text messages (with or without entities). For messages with media
    # (photo/video/document), aiogram populates the caption in .caption;
    # .text will be None — we treat that as "send the text only, not media".
    text = message.text or message.caption
    if text is None:
        return await message.answer(
            "Please send text (or use 🖼 Set Media for photo/video)."
        )

    data = await state.get_data()
    chat_id = data['chat_id']

    chat = await chat_repo.get(chat_id) or {}
    settings = chat.get('welcome_settings') or {}
    # Use html_text so Telegram re-parses the user-supplied entities; if the
    # user pasted plain text this is a no-op.
    settings['text'] = message.html_text if message.text else (message.caption or '')
    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})

    await state.clear()
    await _show_welcome_editor(message, chat_repo, chat_id, edit=False)


# --------------------------------------------------------------------------- #
# Set media (photo or video)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('welcome:set_media:'))
async def start_set_media(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(':')[2])
    await state.set_state(WelcomeStates.waiting_media)
    await state.update_data(chat_id=chat_id)
    await callback.message.answer(
        "🖼 <b>Send the photo or video</b> to attach to your welcome message.\n"
        "The text will come from the welcome text editor; if you send a "
        "caption, it will replace the existing text.\n\n"
        "Send /cancel to abort."
    )
    await callback.answer()


@router.message(WelcomeStates.waiting_media, Command('cancel'))
async def cancel_set_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.waiting_media)
async def receive_welcome_media(message: Message, state: FSMContext, chat_repo):
    data = await state.get_data()
    chat_id = data['chat_id']

    file_id: str | None = None
    media_type: str | None = None
    if message.photo:
        file_id = message.photo[-1].file_id  # largest size
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.animation:
        file_id = message.animation.file_id
        media_type = 'animation'
    elif message.document:
        file_id = message.document.file_id
        media_type = 'document'
    else:
        return await message.answer(
            "Please send a photo, video, GIF, or document. Or /cancel."
        )

    chat = await chat_repo.get(chat_id) or {}
    settings = chat.get('welcome_settings') or {}
    settings['media_file_id'] = file_id
    settings['media_type'] = media_type
    # If the user supplied a caption with the media, treat it as the new text
    # (overwriting any prior text) — this is what the prompt promised.
    if message.caption:
        settings['text'] = message.html_text or message.caption

    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})
    await state.clear()
    await _show_welcome_editor(message, chat_repo, chat_id, edit=False)


# --------------------------------------------------------------------------- #
# Preview — render the saved welcome message into the chat so the admin can
# see exactly what new members will get. Premium emoji tags are sent through
# as-is (Telegram re-renders them).
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('welcome:preview:'))
async def preview_welcome(callback: CallbackQuery, chat_repo, bot):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.", show_alert=True)

    welcome = chat.get('welcome_settings') or {}
    text = welcome.get('text') or '👋 Welcome!'
    media_id = welcome.get('media_file_id')
    media_type = welcome.get('media_type', 'photo')
    settings_doc = await chat_repo.get_chat_settings(chat_id) or {}
    buttons = settings_doc.get('welcome_buttons', []) or chat.get('welcome_buttons', []) or []

    # Build keyboard from stored buttons (row/text/url).
    markup = None
    if buttons:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        rows: dict[int, list] = {}
        for b in buttons:
            row_idx = int(b.get('row', 1))
            rows.setdefault(row_idx, []).append(
                InlineKeyboardButton(text=b['text'][:64], url=b.get('url'))
            )
        markup = InlineKeyboardMarkup(inline_keyboard=[rows[i] for i in sorted(rows)])

    try:
        if media_id and media_type == 'photo':
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=media_id,
                caption=text[:1024],
                reply_markup=markup,
            )
        elif media_id and media_type == 'video':
            await bot.send_video(
                chat_id=callback.from_user.id,
                video=media_id,
                caption=text[:1024],
                reply_markup=markup,
            )
        elif media_id and media_type == 'animation':
            await bot.send_animation(
                chat_id=callback.from_user.id,
                animation=media_id,
                caption=text[:1024],
                reply_markup=markup,
            )
        elif media_id and media_type == 'document':
            await bot.send_document(
                chat_id=callback.from_user.id,
                document=media_id,
                caption=text[:1024],
                reply_markup=markup,
            )
        else:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text[:4096],
                reply_markup=markup,
            )
    except Exception as e:
        return await callback.answer(f"Preview failed: {e}", show_alert=True)
    await callback.answer("Preview sent to your DM ⤵️")


# --------------------------------------------------------------------------- #
# Clear all welcome content for a chat.
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith('welcome:clear:'))
async def clear_welcome(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id) or {}
    settings = chat.get('welcome_settings') or {}
    # Preserve only structural fields; drop text + media.
    settings.pop('text', None)
    settings.pop('media_file_id', None)
    settings.pop('media_type', None)
    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})
    # Buttons live in chat_settings (legacy field); clear them there too so
    # the editor's ✅ indicator updates.
    settings_doc = await chat_repo.get_chat_settings(chat_id) or {}
    if 'welcome_buttons' in settings_doc:
        await chat_repo.update_settings(chat_id, {'welcome_buttons': []})
    await callback.answer("Welcome message cleared.")
    await _show_welcome_editor(
        callback.message, chat_repo, chat_id, edit=True, bot=callback.bot
    )
