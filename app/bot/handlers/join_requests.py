from aiogram import Router, Bot, F
from aiogram.types import ChatJoinRequest, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.logging import get_logger

router = Router()
logger = get_logger('join_requests')


@router.chat_join_request()
async def handle_join_request(
    event: ChatJoinRequest,
    bot: Bot,
    join_request_repo,
    chat_repo,
):
    """
    Main join request handler.

    Two modes (driven by chat_settings.captcha_enabled):
    - Captcha OFF (default): record + approve immediately via Telegram API.
    - Captcha ON: DM the user an "I'm not a robot" button. Approval only
      happens when they click it.

    NOTE: previously this handler only stored the request and relied on
    the approval worker to do the Telegram call. The worker only picks
    up requests with `scheduled_for` set — for delay=0 there was no
    trigger at all, so users were silently never approved. Approve
    inline here (the Telegram API is fast and idempotent).
    """
    user_id = event.from_user.id
    chat_id = event.chat.id

    # Look up chat settings to decide mode
    settings = await chat_repo.get_chat_settings_with_defaults(chat_id)
    captcha_enabled = bool(settings.get("captcha_enabled", False))

    # Persist the request regardless of mode
    await join_request_repo.create({
        "user_id": user_id,
        "chat_id": chat_id,
        "status": "pending",
        "captcha_required": captcha_enabled,
    })

    if captcha_enabled:
        # DM the user with a verification button
        try:
            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ I'm not a robot",
                callback_data=f"captcha:verify:{chat_id}:{user_id}",
            )
            chat_title = event.chat.title or "the group"
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"Hello <b>{event.from_user.first_name or ''}</b>,\n\n"
                    f"To join <b>{chat_title}</b> confirm that you are not a robot "
                    f"by tapping the button below. ⬇️"
                ),
                reply_markup=builder.as_markup(),
            )
        except Exception as e:
            # User has not started the bot — Telegram won't let us DM.
            # Fall back to auto-approve so they aren't locked out.
            logger.warning("Captcha DM failed, falling back to auto-approve",
                           chat_id=chat_id, user_id=user_id, error=str(e))
            try:
                await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
                await join_request_repo.update(
                    {"user_id": user_id, "chat_id": chat_id},
                    {"status": "approved", "captcha_required": False},
                )
            except Exception as e2:
                logger.error("Auto-approve fallback failed",
                             chat_id=chat_id, user_id=user_id, error=str(e2))
        return

    # Captcha OFF path: approve immediately.
    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        await join_request_repo.update(
            {"user_id": user_id, "chat_id": chat_id},
            {"status": "approved"},
        )
        logger.info("Join request approved",
                    chat_id=chat_id, user_id=user_id)
    except Exception as e:
        logger.error("Failed to approve join request",
                     chat_id=chat_id, user_id=user_id, error=str(e))


@router.callback_query(lambda c: c.data and c.data.startswith("captcha:verify:"))
async def captcha_verify_callback(callback: CallbackQuery, bot: Bot, join_request_repo):
    """User clicked 'I'm not a robot' — approve the pending join request."""
    if not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) < 4:
        return await callback.answer("Invalid request.", show_alert=True)
    try:
        chat_id = int(parts[2])
        user_id = int(parts[3])
    except (TypeError, ValueError):
        return await callback.answer("Invalid request.", show_alert=True)

    # Only the original requester can click their own captcha button
    if callback.from_user.id != user_id:
        return await callback.answer("This isn't your captcha.", show_alert=True)

    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
    except Exception as e:
        await callback.answer(f"Failed to approve: {e}", show_alert=True)
        return

    await join_request_repo.update(
        {"user_id": user_id, "chat_id": chat_id},
        {"status": "approved", "captcha_required": False},
    )
    try:
        await callback.message.edit_text("✅ Verified! You are approved. 🎉")
    except Exception:
        pass
    await callback.answer("Approved!")
