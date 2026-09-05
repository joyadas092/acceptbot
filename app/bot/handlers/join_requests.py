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
    user_repo,
):
    """
    Main join request handler.

    Two modes (driven by chat_settings.captcha_enabled):
    - Captcha OFF (default): record + approve immediately via Telegram API.
    - Captcha ON: DM the user an "I'm not a robot" button. Approval only
      happens when they click it.

    On every approval (captcha-off or captcha-fallback) we also upsert
    the user into the `users` collection so they show up in /stats and
    are eligible for /broadcast. AuthMiddleware does this for /start but
    not for chat_join_request updates.
    """
    user_id = event.from_user.id
    chat_id = event.chat.id
    from_user = event.from_user  # aiogram User object

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
            await _approve_and_track(
                bot=bot,
                join_request_repo=join_request_repo,
                user_repo=user_repo,
                from_user=from_user,
                chat_id=chat_id,
                user_id=user_id,
                extra_status_patch={"captcha_required": False},
            )
        return

    # Captcha OFF path: approve immediately.
    await _approve_and_track(
        bot=bot,
        join_request_repo=join_request_repo,
        user_repo=user_repo,
        from_user=from_user,
        chat_id=chat_id,
        user_id=user_id,
    )


async def _approve_and_track(
    bot: Bot,
    join_request_repo,
    user_repo,
    from_user,
    chat_id: int,
    user_id: int,
    extra_status_patch: dict | None = None,
) -> None:
    """
    Approve a join request and upsert the user into the `users`
    collection so they appear in /stats and /broadcast. Used by both the
    captcha-off path and the captcha-DM-failure fallback.
    """
    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
    except Exception as e:
        logger.error("Telegram approve_chat_join_request failed",
                     chat_id=chat_id, user_id=user_id, error=str(e))
        return

    status_patch = {"status": "approved"}
    if extra_status_patch:
        status_patch.update(extra_status_patch)
    await join_request_repo.update(
        {"user_id": user_id, "chat_id": chat_id},
        status_patch,
    )

    # Track the user so they show up in stats + broadcast targets.
    try:
        await user_repo.upsert({
            "telegram_id": from_user.id,
            "username": from_user.username,
            "first_name": from_user.first_name,
            "last_name": from_user.last_name,
            "language_code": from_user.language_code,
            "is_bot": False,
            "is_active": True,
        })
        logger.info("Join request approved + user tracked",
                    chat_id=chat_id, user_id=user_id,
                    username=from_user.username)
    except Exception as e:
        logger.error("User upsert failed (approved but not tracked)",
                     chat_id=chat_id, user_id=user_id, error=str(e))


@router.callback_query(lambda c: c.data and c.data.startswith("captcha:verify:"))
async def captcha_verify_callback(
    callback: CallbackQuery,
    bot: Bot,
    join_request_repo,
    user_repo,
):
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

    # Also upsert the user (the captcha click proves the user has /started
    # the bot, so they should appear in broadcast targets).
    try:
        await user_repo.upsert({
            "telegram_id": callback.from_user.id,
            "username": callback.from_user.username,
            "first_name": callback.from_user.first_name,
            "last_name": callback.from_user.last_name,
            "language_code": callback.from_user.language_code,
            "is_bot": False,
            "is_active": True,
        })
    except Exception as e:
        logger.error("Captcha user upsert failed",
                     user_id=user_id, error=str(e))

    try:
        await callback.message.edit_text("✅ Verified! You are approved. 🎉")
    except Exception:
        pass
    await callback.answer("Approved!")
