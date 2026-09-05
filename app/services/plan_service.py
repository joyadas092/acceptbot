from typing import Dict, Any, List, Optional
from app.database.repositories import SubscriptionRepository

class PlanService:
    def __init__(self, subscription_repo: SubscriptionRepository):
        self.repo = subscription_repo

    async def get_all_plans(self) -> List[Dict[str, Any]]:
        # Usually from DB, static for skeleton
        return [
            {"plan_id": "free", "name": "Free", "price": 0},
            {"plan_id": "premium", "name": "Premium", "price": 9.99}
        ]

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        plans = await self.get_all_plans()
        for p in plans:
            if p["plan_id"] == plan_id:
                return p
        return None

    async def create_or_update_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Super admin: create or update a plan."""
        # For a full implementation, you'd store this in a Plans collection.
        return plan_data

    async def get_user_plan_info(self, user_id: int) -> Dict[str, Any]:
        """Return formatted plan info for display to user."""
        sub = await self.repo.get_by_user_id(user_id)
        if not sub or sub.get("plan_id") == "free":
            return {"plan_name": "Free", "status": "Active", "expires_at": None}
            
        plan = await self.get_plan(sub["plan_id"])
        return {
            "plan_name": plan["name"] if plan else sub["plan_id"],
            "status": sub.get("status"),
            "expires_at": sub.get("expires_at")
        }
