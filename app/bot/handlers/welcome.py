from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from ..keyboards.welcome_menu import (
    welcome_editor_keyboard,
    welcome_timing_keyboard,
    welcome_buttons_keyboard,
    welcome_chat_picker_keyboard,
)

router = Router()


class WelcomeStates(StatesGroup):
    editing_text = State()
    waiting_media = State()
    waiting_btn_text = State()
    waiting_btn_url = State()
    waiting_custom_delay = State()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _get_welcome_settings(chat_repo, chat_id: int) -> dict:
    """Load welcome settings from chat_settings collection with defaults."""
    settings = await chat_repo.get_chat_settings(chat_id) or {}
    return {
        "welcome_enabled": settings.get("welcome_enabled", True),
        "welcome_trigger": settings.get("welcome_trigger", "on_approval"),
        "welcome_delay_seconds": settings.get("welcome_delay_seconds", 0),
        "welcome_text": settings.get("welcome_text", ""),
        "welcome_media_file_id": settings.get("welcome_media_file_id", ""),
        "welcome_media_type": settings.get("welcome_media_type", ""),
        "welcome_buttons": settings.get("welcome_buttons", []),
        "welcome_parse_mode": settings.get("welcome_parse_mode", "HTML"),
    }


async def _render_editor(target, chat_repo, chat_id: int, *, edit: bool = False):
    """Render the welcome editor panel. target = Message object."""
    chat = await chat_repo.get(chat_id)
    if not chat:
        txt = "❌ Chat not found."
        return await (target.edit_text(txt) if edit else target.answer(txt))

    ws = await _get_welcome_settings(chat_repo, chat_id)
    title = chat.get("title", "this chat")

    body = (
        f"👋 <b>Welcome Editor — {title}</b>\n\n"
        "Configure what newly-approved members receive.\n"
        "✅ marks what's already set.\n\n"
        "<b>Current timing:</b> "
        + _trigger_summary(ws["welcome_trigger"], ws["welcome_delay_seconds"])
    )

    markup = welcome_editor_keyboard(
        chat_id=chat_id,
        enabled=ws["welcome_enabled"],
        has_text=bool(ws["welcome_text"]),
        has_media=bool(ws["welcome_media_file_id"]),
        btn_count=len(ws["welcome_buttons"]),
        trigger=ws["welcome_trigger"],
        delay=ws["welcome_delay_seconds"],
    )

    if edit:
        return await target.edit_text(body, reply_markup=markup)
    return await target.answer(body, reply_markup=markup)


def _trigger_summary(trigger: str, delay: int) -> str:
    if trigger == "on_request":
        return "📩 When request arrives"
    if delay == 300:
        return "⏱ 5 min after approval"
    if delay == 600:
        return "⏱ 10 min after approval"
    if delay == 1800:
        return "⏱ 30 min after approval"
    if delay > 0:
        return f"⏱ {delay // 60} min after approval"
    return "✅ On approval"


def _build_preview_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    rows: dict[int, list] = {}
    for btn in buttons:
        row_idx = int(btn.get("row", 1))
        rows.setdefault(row_idx, []).append(
            InlineKeyboardButton(text=btn["text"][:64], url=btn.get("url"))
        )
    return InlineKeyboardMarkup(inline_keyboard=[rows[i] for i in sorted(rows)])


# ──────────────────────────────────────────────────────────────────────────────
# Entry points
# ──────────────────────────────────────────────────────────────────────────────

@router.message(Command("welcome"))
async def welcome_command(message: Message, chat_repo):
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    if not chats:
        return await message.answer(
            "You don't have any connected chats yet.\nAdd me to a group or channel first via /start."
        )
    if len(chats) == 1:
        return await _render_editor(message, chat_repo, chats[0]["chat_id"])
    await message.answer(
        "👋 <b>Welcome Message Setup</b>\n\nSelect the group or channel to configure:",
        reply_markup=welcome_chat_picker_keyboard(chats),
    )


@router.callback_query(F.data == "menu:welcome")
async def welcome_menu_callback(callback: CallbackQuery, chat_repo):
    user_id = callback.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    if not chats:
        return await callback.answer("No connected chats.", show_alert=True)
    if len(chats) == 1:
        await _render_editor(callback.message, chat_repo, chats[0]["chat_id"], edit=True)
        return await callback.answer()
    await callback.message.edit_text(
        "👋 <b>Welcome Message Setup</b>\n\nSelect the group or channel to configure:",
        reply_markup=welcome_chat_picker_keyboard(chats),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:pick:"))
async def welcome_pick_chat(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    await _render_editor(callback.message, chat_repo, chat_id, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:edit:"))
async def welcome_edit_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    await _render_editor(callback.message, chat_repo, chat_id, edit=True)
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Toggle enabled
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:toggle:"))
async def toggle_welcome(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    ws = await _get_welcome_settings(chat_repo, chat_id)
    new_val = not ws["welcome_enabled"]
    await chat_repo.upsert_settings(chat_id, {"welcome_enabled": new_val})
    await _render_editor(callback.message, chat_repo, chat_id, edit=True)
    await callback.answer(f"Welcome {'enabled ✅' if new_val else 'disabled ❌'}")


# ──────────────────────────────────────────────────────────────────────────────
# Edit Text
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:edit_text:"))
async def start_edit_text(callback: CallbackQuery, state: FSMContext, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    ws = await _get_welcome_settings(chat_repo, chat_id)
    current = ws["welcome_text"]
    snippet = (current[:200] + "…" if len(current) > 200 else current) if current else "(empty)"

    await state.set_state(WelcomeStates.editing_text)
    await state.update_data(chat_id=chat_id)
    await callback.message.answer(
        "✏️ <b>Send the new welcome message text.</b>\n\n"
        "<b>Supported variables:</b>\n"
        "• <code>{first_name}</code> — member's first name\n"
        "• <code>{last_name}</code> — last name\n"
        "• <code>{username}</code> — @username\n"
        "• <code>{chat_title}</code> — group/channel name\n\n"
        "<b>Formatting:</b> HTML tags supported "
        "(<code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;a href=…&gt;</code>, "
        "premium emoji <code>&lt;tg-emoji emoji-id=\"…\"&gt;⭐&lt;/tg-emoji&gt;</code>)\n\n"
        f"<b>Current:</b>\n{snippet}\n\n"
        "Send /cancel to abort."
    )
    await callback.answer()


@router.message(WelcomeStates.editing_text, Command("cancel"))
async def cancel_edit_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.editing_text)
async def receive_welcome_text(message: Message, state: FSMContext, chat_repo):
    text = message.html_text or message.text or message.caption or ""
    if not text:
        return await message.answer("Please send text. Or /cancel.")

    data = await state.get_data()
    chat_id = data["chat_id"]
    await chat_repo.upsert_settings(chat_id, {"welcome_text": text})
    await state.clear()
    await message.answer("✅ Welcome text saved!")
    await _render_editor(message, chat_repo, chat_id)


# ──────────────────────────────────────────────────────────────────────────────
# Set Media
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:set_media:"))
async def start_set_media(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    await state.set_state(WelcomeStates.waiting_media)
    await state.update_data(chat_id=chat_id)
    await callback.message.answer(
        "🖼 <b>Send a photo, video, GIF or document</b> to attach to the welcome message.\n\n"
        "• If you include a caption, it will <b>replace</b> the current welcome text.\n"
        "• HTML formatting in captions is preserved.\n\n"
        "Send /cancel to abort."
    )
    await callback.answer()


@router.message(WelcomeStates.waiting_media, Command("cancel"))
async def cancel_set_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.waiting_media)
async def receive_media(message: Message, state: FSMContext, chat_repo):
    file_id: str | None = None
    media_type: str | None = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "animation"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"
    else:
        return await message.answer("Please send a photo, video, GIF or document. Or /cancel.")

    data = await state.get_data()
    chat_id = data["chat_id"]

    updates: dict = {
        "welcome_media_file_id": file_id,
        "welcome_media_type": media_type,
    }
    # If caption provided, save as welcome text too
    if message.caption:
        updates["welcome_text"] = message.html_text or message.caption

    await chat_repo.upsert_settings(chat_id, updates)
    await state.clear()
    await message.answer(f"✅ {media_type.capitalize()} saved!")
    await _render_editor(message, chat_repo, chat_id)


# ──────────────────────────────────────────────────────────────────────────────
# Remove Media
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:remove_media:"))
async def remove_media(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    await chat_repo.upsert_settings(chat_id, {
        "welcome_media_file_id": "",
        "welcome_media_type": "",
    })
    await _render_editor(callback.message, chat_repo, chat_id, edit=True)
    await callback.answer("Media removed.")


# ──────────────────────────────────────────────────────────────────────────────
# Timing / Trigger
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:timing:"))
async def show_timing(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    ws = await _get_welcome_settings(chat_repo, chat_id)
    await callback.message.edit_text(
        "⏰ <b>Welcome Message Timing</b>\n\n"
        "Choose <b>when</b> the welcome message is sent to new members:",
        reply_markup=welcome_timing_keyboard(
            chat_id=chat_id,
            current_trigger=ws["welcome_trigger"],
            current_delay=ws["welcome_delay_seconds"],
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:trigger:"))
async def set_trigger(callback: CallbackQuery, state: FSMContext, chat_repo):
    # format: welcome:trigger:<chat_id>:<mode>  or  welcome:trigger:<chat_id>:delay:<seconds>
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    mode = parts[3]

    if mode == "custom":
        await state.set_state(WelcomeStates.waiting_custom_delay)
        await state.update_data(chat_id=chat_id)
        await callback.message.answer(
            "✏️ Enter the delay in <b>minutes</b> (e.g. <code>15</code> for 15 min):\n"
            "Max 7 days (10080 min). Send /cancel to abort."
        )
        return await callback.answer()

    if mode == "delay":
        seconds = int(parts[4])
        await chat_repo.upsert_settings(chat_id, {
            "welcome_trigger": "delayed",
            "welcome_delay_seconds": seconds,
        })
        label = _trigger_summary("delayed", seconds)
    elif mode == "on_request":
        await chat_repo.upsert_settings(chat_id, {
            "welcome_trigger": "on_request",
            "welcome_delay_seconds": 0,
        })
        label = _trigger_summary("on_request", 0)
    else:  # on_approval
        await chat_repo.upsert_settings(chat_id, {
            "welcome_trigger": "on_approval",
            "welcome_delay_seconds": 0,
        })
        label = _trigger_summary("on_approval", 0)

    ws = await _get_welcome_settings(chat_repo, chat_id)
    await callback.message.edit_text(
        "⏰ <b>Welcome Message Timing</b>\n\n"
        "Choose <b>when</b> the welcome message is sent to new members:",
        reply_markup=welcome_timing_keyboard(
            chat_id=chat_id,
            current_trigger=ws["welcome_trigger"],
            current_delay=ws["welcome_delay_seconds"],
        ),
    )
    await callback.answer(f"Timing set: {label}")


@router.message(WelcomeStates.waiting_custom_delay, Command("cancel"))
async def cancel_custom_delay(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.waiting_custom_delay)
async def receive_custom_delay(message: Message, state: FSMContext, chat_repo):
    if not message.text or not message.text.strip().isdigit():
        return await message.answer("Please enter a valid number of minutes. Or /cancel.")

    minutes = int(message.text.strip())
    if minutes < 1 or minutes > 10080:
        return await message.answer("Must be between 1 and 10080 minutes (7 days). Or /cancel.")

    data = await state.get_data()
    chat_id = data["chat_id"]
    seconds = minutes * 60
    await chat_repo.upsert_settings(chat_id, {
        "welcome_trigger": "delayed",
        "welcome_delay_seconds": seconds,
    })
    await state.clear()
    await message.answer(f"✅ Custom delay set: {minutes} min after approval.")
    await _render_editor(message, chat_repo, chat_id)


# ──────────────────────────────────────────────────────────────────────────────
# Button Manager
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:buttons:"))
async def show_buttons(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    ws = await _get_welcome_settings(chat_repo, chat_id)
    buttons = ws["welcome_buttons"]
    count = len(buttons)
    await callback.message.edit_text(
        f"🔘 <b>Inline Buttons</b> ({count}/10)\n\n"
        + (
            "\n".join(
                f"{i+1}. <b>{b['text']}</b> → <code>{b.get('url','')}</code>"
                for i, b in enumerate(buttons)
            )
            if buttons
            else "No buttons set yet."
        )
        + "\n\nTap a button to remove it, or add a new one.",
        reply_markup=welcome_buttons_keyboard(chat_id, buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:btn_add:"))
async def start_add_button(callback: CallbackQuery, state: FSMContext, chat_repo):
    chat_id = int(callback.data.split(":")[2])
    ws = await _get_welcome_settings(chat_repo, chat_id)
    if len(ws["welcome_buttons"]) >= 10:
        return await callback.answer("Maximum 10 buttons.", show_alert=True)
    await state.set_state(WelcomeStates.waiting_btn_text)
    await state.update_data(chat_id=chat_id)
    await callback.message.answer(
        "🔘 <b>Add Button — Step 1/2</b>\n\nSend the <b>button text</b> (max 64 chars):\n\n"
        "Send /cancel to abort."
    )
    await callback.answer()


@router.message(WelcomeStates.waiting_btn_text, Command("cancel"))
async def cancel_btn_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.waiting_btn_text)
async def receive_btn_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        return await message.answer("Button text cannot be empty. Or /cancel.")
    if len(text) > 64:
        return await message.answer("Max 64 characters. Or /cancel.")
    await state.update_data(btn_text=text)
    await state.set_state(WelcomeStates.waiting_btn_url)
    await message.answer(
        f"🔘 <b>Add Button — Step 2/2</b>\n\nButton text: <b>{text}</b>\n\n"
        "Now send the <b>URL</b> for this button (must start with https:// or http://):\n\n"
        "Send /cancel to abort."
    )


@router.message(WelcomeStates.waiting_btn_url, Command("cancel"))
async def cancel_btn_url(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


@router.message(WelcomeStates.waiting_btn_url)
async def receive_btn_url(message: Message, state: FSMContext, chat_repo):
    url = (message.text or "").strip()
    if not url.startswith(("https://", "http://", "tg://")):
        return await message.answer(
            "Must be a valid URL starting with https://, http://, or tg://\nOr /cancel."
        )

    data = await state.get_data()
    chat_id = data["chat_id"]
    btn_text = data["btn_text"]

    ws = await _get_welcome_settings(chat_repo, chat_id)
    buttons = ws["welcome_buttons"]

    # Determine row: put new button on last row or new row
    last_row = max((b.get("row", 1) for b in buttons), default=0)
    # If last row already has 3 buttons, start a new row
    last_row_count = sum(1 for b in buttons if b.get("row") == last_row)
    row = last_row + 1 if last_row_count >= 3 else max(last_row, 1)

    buttons.append({"text": btn_text, "url": url, "row": row})
    await chat_repo.upsert_settings(chat_id, {"welcome_buttons": buttons})
    await state.clear()

    await message.answer(f"✅ Button added: <b>{btn_text}</b> → {url}")
    await _render_editor(message, chat_repo, chat_id)


@router.callback_query(F.data.startswith("welcome:btn_remove:"))
async def remove_button(callback: CallbackQuery, chat_repo):
    parts = callback.data.split(":")
    chat_id = int(parts[2])
    index = int(parts[3])

    ws = await _get_welcome_settings(chat_repo, chat_id)
    buttons = ws["welcome_buttons"]
    if 0 <= index < len(buttons):
        removed = buttons.pop(index)
        await chat_repo.upsert_settings(chat_id, {"welcome_buttons": buttons})
        await callback.answer(f"Removed: {removed['text']}")
    else:
        await callback.answer("Button not found.")

    # Refresh buttons panel
    ws2 = await _get_welcome_settings(chat_repo, chat_id)
    count = len(ws2["welcome_buttons"])
    await callback.message.edit_text(
        f"🔘 <b>Inline Buttons</b> ({count}/10)\n\n"
        + (
            "\n".join(
                f"{i+1}. <b>{b['text']}</b> → <code>{b.get('url','')}</code>"
                for i, b in enumerate(ws2["welcome_buttons"])
            )
            if ws2["welcome_buttons"]
            else "No buttons set yet."
        )
        + "\n\nTap a button to remove it, or add a new one.",
        reply_markup=welcome_buttons_keyboard(chat_id, ws2["welcome_buttons"]),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Preview
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("welcome:preview:"))
async def preview_welcome(callback: CallbackQuery, chat_repo, bot):
    chat_id = int(callback.data.split(":")[2])
    chat = await chat_repo.get(chat_id)
    ws = await _get_welcome_settings(chat_repo, chat_id)

    # Substitute variables with dummy data for preview
    text = ws["welcome_text"] or "👋 Welcome!"
    text = (
        text
        .replace("{first_name}", callback.from_user.first_name or "John")
        .replace("{last_name}", callback.from_user.last_name or "Doe")
        .replace("{username}", f"@{callback.from_user.username}" if callback.from_user.username else "@johndoe")
        .replace("{chat_title}", (chat or {}).get("title", "Your Group"))
        .replace("{user_id}", str(callback.from_user.id))
    )

    keyboard = _build_preview_keyboard(ws["welcome_buttons"])
    media_id = ws["welcome_media_file_id"]
    media_type = ws["welcome_media_type"]
    user_id = callback.from_user.id

    try:
        if media_id and media_type == "photo":
            await bot.send_photo(chat_id=user_id, photo=media_id,
                                 caption=text[:1024] if text else None,
                                 parse_mode="HTML", reply_markup=keyboard)
        elif media_id and media_type == "video":
            await bot.send_video(chat_id=user_id, video=media_id,
                                 caption=text[:1024] if text else None,
                                 parse_mode="HTML", reply_markup=keyboard)
        elif media_id and media_type == "animation":
            await bot.send_animation(chat_id=user_id, animation=media_id,
                                     caption=text[:1024] if text else None,
                                     parse_mode="HTML", reply_markup=keyboard)
        elif media_id and media_type == "document":
            await bot.send_document(chat_id=user_id, document=media_id,
                                    caption=text[:1024] if text else None,
                                    parse_mode="HTML", reply_markup=keyboard)
        else:
            await bot.send_message(chat_id=user_id, text=text[:4096],
                                   parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("👁 Preview sent to your DM ⤵️")
    except Exception as e:
        await callback.answer(f"Preview failed: {str(e)[:100]}", show_alert=True)
