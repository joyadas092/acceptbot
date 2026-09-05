from typing import Dict, Any

from app.database.repositories import ChatRepository, JoinRequestRepository, UserRepository, BroadcastRepository

class StatsService:
    def __init__(
        self,
        chat_repo: ChatRepository,
        join_request_repo: JoinRequestRepository,
        user_repo: UserRepository,
        broadcast_repo: BroadcastRepository
    ):
        self.chat_repo = chat_repo
        self.join_request_repo = join_request_repo
        self.user_repo = user_repo
        self.broadcast_repo = broadcast_repo

    async def get_chat_stats(self, chat_id: int) -> Dict[str, Any]:
        """Per-chat statistics."""
        # In a real app, you'd cache this or maintain running counters
        pending = await self.join_request_repo.collection.count_documents({"chat_id": chat_id, "status": "pending"})
        approved = await self.join_request_repo.collection.count_documents({"chat_id": chat_id, "status": "approved"})
        failed = await self.join_request_repo.collection.count_documents({"chat_id": chat_id, "status": "failed"})
        
        total = pending + approved + failed
        rate = (approved / total * 100) if total > 0 else 0
        
        return {
            "pending": pending,
            "total_approved": approved,
            "failed": failed,
            "approval_rate": round(rate, 2)
        }

    async def get_global_stats(self) -> Dict[str, Any]:
        """Super admin global statistics."""
        total_users = await self.user_repo.collection.count_documents({})
        total_chats = await self.chat_repo.collection.count_documents({})
        total_requests = await self.join_request_repo.collection.estimated_document_count()
        total_broadcasts = await self.broadcast_repo.collection.estimated_document_count()
        
        return {
            "users": total_users,
            "chats": total_chats,
            "join_requests": total_requests,
            "broadcasts": total_broadcasts
        }

    async def get_system_stats(
        self,
        db_manager: Any,
        redis_client: Any
    ) -> Dict[str, Any]:
        """MongoDB ping, Redis ping, connection pool info."""
        mongo_ok = False
        try:
            await db_manager.db.command("ping")
            mongo_ok = True
        except:
            pass
            
        redis_ok = False
        try:
            await redis_client.ping()
            redis_ok = True
        except:
            pass
            
        return {
            "mongodb": "online" if mongo_ok else "offline",
            "redis": "online" if redis_ok else "offline"
        }
