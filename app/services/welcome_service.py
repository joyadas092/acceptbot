from typing import Dict, Any, List
from datetime import datetime, timedelta

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
        telegram_service: TelegramService
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
        Send welcome message to a user.
        """
        if not settings.get("welcome_enabled", False):
            return False
            
        if settings.get("welcome_trigger") != trigger:
            return False
            
        chat_doc = await self.chat_repo.get_by_chat_id(request_doc["chat_id"])
        if not chat_doc:
            return False
            
        text = self.build_welcome_text(settings.get("welcome_text", ""), request_doc, chat_doc)
        keyboard = self.build_welcome_keyboard(settings.get("welcome_buttons", []))
        
        success = await self.telegram_service.send_message(
            chat_id=request_doc["user_id"],
            text=text,
            reply_markup=keyboard
        )
        
        status = "sent" if success else "failed"
        
        await self.join_request_repo.update(
            {"_id": request_doc["_id"]},
            {"welcome_status": status, "welcome_sent_at": utcnow() if success else None}
        )
        
        return success

    def build_welcome_text(
        self,
        template: str,
        request_doc: Dict[str, Any],
        chat_doc: Dict[str, Any]
    ) -> str:
        """Substitute variables in welcome text."""
        # Note: request_doc needs to contain user info, or we should fetch it.
        # For this skeleton, assuming we just have basic info.
        safe_template = template.replace("{chat_title}", chat_doc.get("title", "this chat"))
        return safe_template

    def build_welcome_keyboard(
        self,
        buttons: List[Dict[str, Any]]
    ) -> InlineKeyboardMarkup:
        """
        Build InlineKeyboardMarkup from buttons list.
        """
        if not buttons:
            return None
            
        rows = {}
        for btn in buttons:
            row_idx = btn.get("row", 0)
            if row_idx not in rows:
                rows[row_idx] = []
            rows[row_idx].append(InlineKeyboardButton(text=btn["text"], url=btn.get("url")))
            
        keyboard_rows = [rows[i] for i in sorted(rows.keys())]
        return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

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
        Process delayed welcome messages that are due.
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
