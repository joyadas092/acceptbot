from typing import Dict, Any, List
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.repositories import JoinRequestRepository, ChatRepository
from app.services.telegram_service import TelegramService
from app.core.logging import get_logger
from app.core.utils import utcnow

class WelcomeService:
    def __init__(
        self,
        join_request_repo: JoinRequestRepository,
        chat_repo: ChatRepository,
        telegram_service: TelegramService,
    ):
        self.join_request_repo = join_request_repo
        self.chat_repo = chat_repo
        self.telegram_service = telegram_service
        self.logger = get_logger('welcome_service')

    async def send_welcome(
        self,
        request_doc: Dict[str, Any],
        settings: Dict[str, Any],
        trigger: str
    ) -> bool:
        """
        Send welcome DM to a newly approved member.

        Content lives on the chat document under `welcome_settings`:
          - text          (str, may be empty)
          - media_file_id (str) + media_type ('photo'|'video'|'animation'|'document')
          - buttons       (list of {text, url, row})  — see build_welcome_keyboard

        The `settings` argument still carries the enable flag + optional
        trigger guard for legacy callers.
        """
        if not settings.get("welcome_enabled", False):
            return False

        # Optional trigger guard. New installations don't set this; we treat
        # missing as "send on every approval".
        if settings.get("welcome_trigger") and settings.get("welcome_trigger") != trigger:
            return False

        chat_doc = await self.chat_repo.get_by_chat_id(request_doc["chat_id"])
        if not chat_doc:
            return False

        welcome = chat_doc.get("welcome_settings") or {}
        text = self.build_welcome_text(
            welcome.get("text", ""), request_doc, chat_doc
        )
        keyboard = self.build_welcome_keyboard(chat_doc.get("welcome_buttons", []) or [])
        media_file_id = welcome.get("media_file_id")
        media_type = welcome.get("media_type", "photo")

        if not text and not media_file_id:
            # Nothing configured — skip silently rather than spamming empty.
            return False

        bot: Bot = getattr(self.telegram_service, "bot", None)
        user_id = request_doc["user_id"]
        ok = False
        try:
            if bot is not None and media_file_id:
                if media_type == "photo":
                    sent = await bot.send_photo(
                        chat_id=user_id, photo=media_file_id,
                        caption=text[:1024] or None, reply_markup=keyboard,
                    )
                elif media_type == "video":
                    sent = await bot.send_video(
                        chat_id=user_id, video=media_file_id,
                        caption=text[:1024] or None, reply_markup=keyboard,
                    )
                elif media_type == "animation":
                    sent = await bot.send_animation(
                        chat_id=user_id, animation=media_file_id,
                        caption=text[:1024] or None, reply_markup=keyboard,
                    )
                elif media_type == "document":
                    sent = await bot.send_document(
                        chat_id=user_id, document=media_file_id,
                        caption=text[:1024] or None, reply_markup=keyboard,
                    )
                else:
                    sent = await bot.send_message(
                        chat_id=user_id, text=text[:4096], reply_markup=keyboard,
                    )
                ok = sent is not None
            else:
                ok = await self.telegram_service.send_message(
                    chat_id=user_id, text=text[:4096], reply_markup=keyboard,
                )
        except Exception as e:
            self.logger.warning("send_welcome failed", error=str(e))
            ok = False

        status = "sent" if ok else "failed"
        await self.join_request_repo.update(
            {"_id": request_doc["_id"]},
            {"welcome_status": status, "welcome_sent_at": utcnow() if ok else None}
        )
        return ok

    def build_welcome_text(
        self,
        template: str,
        request_doc: Dict[str, Any],
        chat_doc: Dict[str, Any]
    ) -> str:
        """Substitute variables in welcome text. Preserves HTML / premium-emoji markup."""
        if not template:
            return ""
        return template.replace("{chat_title}", chat_doc.get("title", "this chat"))

    def build_welcome_keyboard(
        self,
        buttons: List[Dict[str, Any]]
    ) -> InlineKeyboardMarkup:
        """
        Build InlineKeyboardMarkup from buttons list. Buttons are sorted
        by `row` so multi-row layouts render predictably.
        """
        if not buttons:
            return None
        rows: Dict[int, list] = {}
        for btn in buttons:
            row_idx = int(btn.get("row", 1))
            if row_idx not in rows:
                rows[row_idx] = []
            rows[row_idx].append(InlineKeyboardButton(
                text=str(btn["text"])[:64],
                url=btn.get("url"),
            ))
        return InlineKeyboardMarkup(inline_keyboard=[rows[i] for i in sorted(rows)])

    async def schedule_welcome(
        self,
        request_id: str,
        delay_seconds: int
    ) -> None:
        schedule_time = utcnow() + timedelta(seconds=delay_seconds)
        await self.join_request_repo.update(
            {"_id": request_id},
            {"welcome_scheduled_for": schedule_time, "welcome_status": "scheduled"}
        )

    async def process_due_welcome_messages(
        self,
        now: datetime
    ) -> int:
        """
        Worker-side: find scheduled welcomes whose time has come and send them.
        """
        due_welcomes = await self.join_request_repo.find({
            "welcome_status": "scheduled",
            "welcome_scheduled_for": {"$lte": now}
        })

        count = 0
        for req in due_welcomes:
            settings = await self.chat_repo.get_chat_settings(req["chat_id"])
            if settings:
                if await self.send_welcome(req, settings, "delayed"):
                    count += 1
        return count
