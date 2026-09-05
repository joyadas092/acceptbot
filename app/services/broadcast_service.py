from typing import Dict, Any, List, Optional
from datetime import datetime

from app.database.repositories import BroadcastRepository, JoinRequestRepository, UserRepository, ChatRepository
from app.services.entitlement_service import EntitlementService
from app.services.telegram_service import TelegramService
from app.services.rate_limiter import TelegramRateLimiter
from app.core.logging import get_logger
from app.core.utils import generate_job_id, utcnow

class BroadcastService:
    def __init__(
        self,
        broadcast_repo: BroadcastRepository,
        join_request_repo: JoinRequestRepository,
        user_repo: UserRepository,
        chat_repo: ChatRepository,
        entitlement_service: EntitlementService,
        telegram_service: TelegramService,
        rate_limiter: TelegramRateLimiter
    ):
        self.broadcast_repo = broadcast_repo
        self.join_request_repo = join_request_repo
        self.user_repo = user_repo
        self.chat_repo = chat_repo
        self.entitlement_service = entitlement_service
        self.telegram_service = telegram_service
        self.rate_limiter = rate_limiter
        self.logger = get_logger('broadcast_service')

    async def create_broadcast_job(
        self,
        owner_id: int,
        target_type: str,  # 'chat', 'all_chats', 'master'
        message_payload: Dict[str, Any],
        chat_id: Optional[int] = None,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Create a broadcast job in DRAFT status.
        Check entitlements first.
        """
        can_broadcast, reason = await self.entitlement_service.can_broadcast(owner_id)
        if not can_broadcast:
            raise ValueError(f"Broadcast not allowed: {reason}")
            
        job_id = generate_job_id()
        job_data = {
            "job_id": job_id,
            "owner_id": owner_id,
            "target_type": target_type,
            "chat_id": chat_id,
            "message_payload": message_payload,
            "deduplicate": deduplicate,
            "status": "draft",
            "progress": {"total": 0, "sent": 0, "failed": 0},
            "created_at": utcnow(),
            "updated_at": utcnow()
        }
        
        await self.broadcast_repo.collection.insert_one(job_data)
        return job_data

    async def prepare_recipients(
        self,
        job_id: str
    ) -> int:
        """
        Populate broadcast_recipients collection for this job.
        This is async and may take time — run in worker, not handler.
        """
        job = await self.broadcast_repo.get_by_job_id(job_id)
        if not job:
            return 0
            
        owner_id = job["owner_id"]
        max_recips = await self.entitlement_service.get_max_recipients(owner_id)
        
        # Simple implementation: fetch users from join requests
        query = {}
        if job["target_type"] == "chat" and job.get("chat_id"):
            query["chat_id"] = job["chat_id"]
        elif job["target_type"] == "all_chats":
            user_chats = await self.chat_repo.find({"connected_by": owner_id})
            chat_ids = [c["chat_id"] for c in user_chats]
            query["chat_id"] = {"$in": chat_ids}
            
        cursor = self.join_request_repo.collection.find(query, {"user_id": 1})
        
        recipients = set()
        async for doc in cursor:
            recipients.add(doc["user_id"])
            
        recip_list = list(recipients)[:max_recips]
        
        if recip_list:
            docs = [{"job_id": job_id, "user_id": u, "status": "pending"} for u in recip_list]
            # Assumes you have a broadcast_recipients collection in repo
            await self.broadcast_repo.db.broadcast_recipients.insert_many(docs)
            
        await self.broadcast_repo.update(
            {"job_id": job_id},
            {"progress.total": len(recip_list)}
        )
        return len(recip_list)

    async def start_job(self, job_id: str, owner_id: int) -> bool:
        """Transition job from DRAFT → PENDING (worker picks it up)."""
        res = await self.broadcast_repo.update(
            {"job_id": job_id, "owner_id": owner_id, "status": "draft"},
            {"status": "pending", "updated_at": utcnow()}
        )
        return res.modified_count > 0

    async def pause_job(self, job_id: str, owner_id: int) -> bool:
        """Pause a running job. Worker will stop after current batch."""
        res = await self.broadcast_repo.update(
            {"job_id": job_id, "owner_id": owner_id, "status": "running"},
            {"status": "paused", "updated_at": utcnow()}
        )
        return res.modified_count > 0

    async def resume_job(self, job_id: str, owner_id: int) -> bool:
        """Resume a paused job."""
        res = await self.broadcast_repo.update(
            {"job_id": job_id, "owner_id": owner_id, "status": "paused"},
            {"status": "pending", "updated_at": utcnow()}
        )
        return res.modified_count > 0

    async def cancel_job(self, job_id: str, owner_id: int) -> bool:
        """Cancel a job (cannot be undone)."""
        res = await self.broadcast_repo.update(
            {"job_id": job_id, "owner_id": owner_id, "status": {"$in": ["draft", "pending", "paused", "running"]}},
            {"status": "cancelled", "updated_at": utcnow()}
        )
        return res.modified_count > 0

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job with progress."""
        return await self.broadcast_repo.get_by_job_id(job_id)

    async def get_user_jobs(self, owner_id: int) -> List[Dict[str, Any]]:
        """Get recent broadcast jobs for a user."""
        cursor = self.broadcast_repo.collection.find({"owner_id": owner_id}).sort("created_at", -1).limit(10)
        return await cursor.to_list(length=10)

    async def get_recipient_estimate(
        self,
        owner_id: int,
        target_type: str,
        chat_id: Optional[int] = None,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """Fast estimate of recipient count before creating job."""
        # This is an approximation
        count = 100 # Default dummy value for skeleton
        return {
            "estimated_total": count,
            "after_dedup": count,
            "removed_duplicates": 0
        }
