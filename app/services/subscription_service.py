from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.database.repositories import SubscriptionRepository
from app.core.utils import utcnow

class SubscriptionService:
    def __init__(self, subscription_repo: SubscriptionRepository):
        self.repo = subscription_repo

    async def get_user_subscription(self, user_id: int) -> Dict[str, Any]:
        """Returns active subscription or free defaults."""
        sub = await self.repo.get_by_user_id(user_id)
        if sub and sub.get("status") == "active" and sub.get("expires_at", utcnow()) > utcnow():
            return sub
            
        return {
            "user_id": user_id,
            "plan_id": "free",
            "status": "active",
            "expires_at": utcnow() + timedelta(days=36500) # never expires essentially
        }

    async def get_plan_limits(self, user_id: int) -> Dict[str, Any]:
        """
        Returns dict with:
        - broadcast_enabled
        - max_broadcasts_per_day
        - max_recipients_per_broadcast
        - max_connected_chats
        - plan_tier
        """
        sub = await self.get_user_subscription(user_id)
        plan_id = sub.get("plan_id", "free")
        
        # Hardcoded limits for skeleton. Should fetch from PlanService
        if plan_id == "premium":
            return {
                "broadcast_enabled": True,
                "max_broadcasts_per_day": 10,
                "max_recipients_per_broadcast": 50000,
                "max_connected_chats": 10,
                "plan_tier": "premium"
            }
            
        return {
            "broadcast_enabled": False,
            "max_broadcasts_per_day": 0,
            "max_recipients_per_broadcast": 0,
            "max_connected_chats": 1,
            "plan_tier": "free"
        }

    async def assign_plan(
        self,
        user_id: int,
        plan_id: str,
        duration_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Assign a plan to a user. Super admin action."""
        expires_at = utcnow() + timedelta(days=duration_days) if duration_days else (utcnow() + timedelta(days=30))
        
        data = {
            "user_id": user_id,
            "plan_id": plan_id,
            "status": "active",
            "starts_at": utcnow(),
            "expires_at": expires_at,
            "updated_at": utcnow()
        }
        
        # Upsert logic
        await self.repo.collection.update_one(
            {"user_id": user_id},
            {"$set": data},
            upsert=True
        )
        return data

    async def is_active(self, user_id: int) -> bool:
        """Check if user has an active (non-expired) subscription."""
        sub = await self.get_user_subscription(user_id)
        return sub.get("plan_id") != "free"
