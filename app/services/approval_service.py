from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from aiogram.types import ChatJoinRequest
from redis.asyncio import Redis

from app.database.repositories import JoinRequestRepository, ChatRepository
from app.services.telegram_service import TelegramService
from app.core.logging import get_logger
from app.core.utils import utcnow, generate_job_id

class ApprovalService:
    def __init__(
        self,
        join_request_repo: JoinRequestRepository,
        chat_repo: ChatRepository,
        telegram_service: TelegramService,
        welcome_service: Any,  # forward ref
        redis_client: Redis
    ):
        self.join_request_repo = join_request_repo
        self.chat_repo = chat_repo
        self.telegram_service = telegram_service
        self.welcome_service = welcome_service
        self.redis = redis_client
        self.logger = get_logger('approval_service')

    async def handle_new_join_request(
        self,
        join_request: ChatJoinRequest
    ) -> None:
        """
        Called by handler when a new ChatJoinRequest arrives.
        """
        chat_id = join_request.chat.id
        user_id = join_request.from_user.id
        
        # Idempotent store
        request_doc = await self.join_request_repo.create_request(chat_id, user_id)
        if not request_doc:
            # Already exists and not pending
            self.logger.info(f"Duplicate/handled request {chat_id}:{user_id}")
            return
            
        settings = await self.chat_repo.get_chat_settings(chat_id)
        if not settings:
            self.logger.warning(f"No settings for chat {chat_id}, ignoring request")
            return
            
        if settings.get("auto_approval_enabled", True):
            delay = settings.get("auto_approval_delay", 0)
            if delay == 0:
                await self.execute_approval(request_doc["_id"], request_doc, settings)
            else:
                schedule_time = utcnow() + timedelta(seconds=delay)
                await self.join_request_repo.update(
                    {"_id": request_doc["_id"]},
                    {"scheduled_for": schedule_time}
                )
                self.logger.info(f"Scheduled approval for {chat_id}:{user_id} at {schedule_time}")
                
        # Send welcome if on_request
        if settings.get("welcome_enabled", False) and settings.get("welcome_trigger") == "on_request":
            await self.welcome_service.send_welcome(request_doc, settings, "on_request")

    async def execute_approval(
        self,
        request_id: str,
        request_doc: Dict[str, Any],
        settings: Dict[str, Any]
    ) -> bool:
        """
        Actually approve the request via Telegram API.
        Uses Redis distributed lock to prevent duplicate processing.
        """
        lock_key = f"lock:approve:{request_id}"
        if not await self._acquire_lock(lock_key):
            return False
            
        try:
            # Check if still pending
            current_doc = await self.join_request_repo.get(request_id)
            if not current_doc or current_doc.get("status") != "pending":
                return True
                
            success = await self.telegram_service.approve_join_request(
                chat_id=request_doc["chat_id"],
                user_id=request_doc["user_id"]
            )
            
            if success:
                await self.join_request_repo.update(
                    {"_id": request_id},
                    {"status": "approved", "processed_at": utcnow()}
                )
                
                # Check welcome trigger
                if settings.get("welcome_enabled", False) and settings.get("welcome_trigger") == "on_approval":
                    await self.welcome_service.send_welcome(current_doc, settings, "on_approval")
                    
                return True
            else:
                await self.join_request_repo.update(
                    {"_id": request_id},
                    {"status": "failed", "processed_at": utcnow()}
                )
                return False
                
        finally:
            await self._release_lock(lock_key)

    async def process_due_requests(
        self,
        now: datetime
    ) -> int:
        """
        Fetches all due scheduled requests. Processes each one with locking.
        """
        due_requests = await self.join_request_repo.find({
            "status": "pending",
            "scheduled_for": {"$lte": now}
        })
        
        count = 0
        for req in due_requests:
            settings = await self.chat_repo.get_chat_settings(req["chat_id"])
            if settings:
                if await self.execute_approval(req["_id"], req, settings):
                    count += 1
                    
        return count

    async def _acquire_lock(
        self, key: str, ttl: int = 60
    ) -> bool:
        """Acquire Redis distributed lock."""
        return await self.redis.set(key, "locked", nx=True, ex=ttl)

    async def _release_lock(self, key: str) -> None:
        """Release Redis lock."""
        await self.redis.delete(key)
