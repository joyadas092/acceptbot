from typing import Tuple

from app.services.subscription_service import SubscriptionService

class EntitlementService:
    def __init__(self, subscription_service: SubscriptionService):
        self.subscription_service = subscription_service

    async def can_broadcast(self, user_id: int) -> Tuple[bool, str]:
        """Returns (allowed, reason). Check plan limits."""
        limits = await self.subscription_service.get_plan_limits(user_id)
        if not limits.get("broadcast_enabled", False):
            return False, "Your plan does not allow broadcasts."
        return True, "Allowed"

    async def can_connect_chat(self, user_id: int, current_count: int) -> Tuple[bool, str]:
        """Check if user can connect more chats based on plan."""
        limits = await self.subscription_service.get_plan_limits(user_id)
        max_chats = limits.get("max_connected_chats", 1)
        if current_count >= max_chats:
            return False, f"You have reached your limit of {max_chats} chats."
        return True, "Allowed"

    async def get_max_recipients(self, user_id: int) -> int:
        """Return max broadcast recipients for user's plan."""
        limits = await self.subscription_service.get_plan_limits(user_id)
        return limits.get("max_recipients_per_broadcast", 0)

    async def can_use_feature(self, user_id: int, feature: str) -> bool:
        """Generic feature flag check."""
        limits = await self.subscription_service.get_plan_limits(user_id)
        # simplistic check based on a hypothetical feature list
        features = limits.get("features", [])
        return feature in features or limits.get("plan_tier") == "premium"
