from typing import Any, Optional
from aiogram import Bot
from aiogram.types import ChatMember, Chat, InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.services.rate_limiter import TelegramRateLimiter
from app.core.logging import get_logger

def is_retryable(exception: BaseException) -> bool:
    return isinstance(exception, (TelegramRetryAfter, ConnectionError, TimeoutError))

class TelegramService:
    def __init__(self, bot: Bot, rate_limiter: TelegramRateLimiter):
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.logger = get_logger('telegram_service')

    @retry(
        retry=retry_if_exception_type((TelegramRetryAfter, ConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3)
    )
    async def approve_join_request(self, chat_id: int, user_id: int) -> bool:
        """
        Approve a join request. Returns True on success, False on permanent failure.
        Handles RetryAfter with retry logic.
        Handles TelegramBadRequest (already approved, etc.) gracefully.
        """
        await self.rate_limiter.acquire_global()
        try:
            await self.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            return True
        except TelegramRetryAfter as e:
            self.logger.warning(f"RetryAfter: {e.retry_after}s on approve request {chat_id}:{user_id}")
            await self.rate_limiter.handle_retry_after(e.retry_after)
            raise e  # Let tenacity retry
        except TelegramBadRequest as e:
            self.logger.info(f"Failed to approve {chat_id}:{user_id} - {e.message}")
            return False
        except TelegramForbiddenError:
            self.logger.warning(f"Bot forbidden in chat {chat_id}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error approving {chat_id}:{user_id} - {e}")
            return False

    @retry(
        retry=retry_if_exception_type((TelegramRetryAfter, ConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3)
    )
    async def decline_join_request(self, chat_id: int, user_id: int) -> bool:
        """Decline a join request."""
        await self.rate_limiter.acquire_global()
        try:
            await self.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            return True
        except TelegramRetryAfter as e:
            await self.rate_limiter.handle_retry_after(e.retry_after)
            raise e
        except Exception as e:
            self.logger.warning(f"Failed to decline {chat_id}:{user_id} - {e}")
            return False

    @retry(
        retry=retry_if_exception_type(TelegramRetryAfter),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3)
    )
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Send a message. Returns True on success.
        Handles: Forbidden (user blocked bot), BadRequest, RetryAfter.
        Logs failures, does NOT raise.
        """
        await self.rate_limiter.acquire_global()
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        except TelegramRetryAfter as e:
            await self.rate_limiter.handle_retry_after(e.retry_after)
            raise e
        except TelegramForbiddenError:
            self.logger.info(f"Bot blocked by user or forbidden in chat {chat_id}")
            return False
        except TelegramBadRequest as e:
            self.logger.warning(f"Bad request sending message to {chat_id} - {e.message}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending message to {chat_id} - {e}")
            return False

    @retry(
        retry=retry_if_exception_type(TelegramRetryAfter),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3)
    )
    async def send_media_message(
        self,
        chat_id: int,
        media_type: str,
        file_id: str,
        caption: Optional[str] = None,
        parse_mode: str = 'HTML',
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Send photo/video/document/audio/animation using file_id."""
        await self.rate_limiter.acquire_global()
        try:
            if media_type == 'photo':
                await self.bot.send_photo(chat_id, file_id, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            elif media_type == 'video':
                await self.bot.send_video(chat_id, file_id, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            elif media_type == 'document':
                await self.bot.send_document(chat_id, file_id, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            elif media_type == 'audio':
                await self.bot.send_audio(chat_id, file_id, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            elif media_type == 'animation':
                await self.bot.send_animation(chat_id, file_id, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                self.logger.error(f"Unsupported media type: {media_type}")
                return False
            return True
        except TelegramRetryAfter as e:
            await self.rate_limiter.handle_retry_after(e.retry_after)
            raise e
        except Exception as e:
            self.logger.warning(f"Failed to send media {media_type} to {chat_id} - {e}")
            return False

    async def get_chat_member(
        self, chat_id: int, user_id: int
    ) -> Optional[ChatMember]:
        """Get chat member status. Returns None on error."""
        await self.rate_limiter.acquire_global()
        try:
            return await self.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        except Exception as e:
            self.logger.warning(f"Failed to get chat member {user_id} in {chat_id}: {e}")
            return None

    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        """Get chat info. Returns None on error."""
        await self.rate_limiter.acquire_global()
        try:
            return await self.bot.get_chat(chat_id=chat_id)
        except Exception as e:
            self.logger.warning(f"Failed to get chat {chat_id}: {e}")
            return None

    async def get_bot_member(
        self, chat_id: int
    ) -> Optional[ChatMember]:
        """Get the bot's own ChatMember in a chat."""
        bot_me = await self.bot.get_me()
        return await self.get_chat_member(chat_id, bot_me.id)

    async def check_bot_can_approve(
        self, chat_id: int
    ) -> tuple[bool, str]:
        """
        Returns (can_approve, reason).
        Checks: bot is admin AND has can_invite_users permission.
        """
        member = await self.get_bot_member(chat_id)
        if not member:
            return False, "Bot is not in the chat or chat not found."
            
        if member.status != 'administrator':
            return False, "Bot is not an administrator."
            
        if not getattr(member, 'can_invite_users', False):
            return False, "Bot lacks 'Invite Users' permission."
            
        return True, "Success"

    @retry(
        retry=retry_if_exception_type(TelegramRetryAfter),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3)
    )
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Edit a message. Returns True on success."""
        await self.rate_limiter.acquire_global()
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except TelegramRetryAfter as e:
            await self.rate_limiter.handle_retry_after(e.retry_after)
            raise e
        except Exception as e:
            self.logger.warning(f"Failed to edit message {message_id} in {chat_id}: {e}")
            return False
