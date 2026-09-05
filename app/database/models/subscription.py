from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class PlanTier(str, Enum):
    FREE = 'free'
    PRO = 'pro'
    BUSINESS = 'business'
    ENTERPRISE = 'enterprise'

class Subscription(BaseModel):
    user_id: int
    plan_id: str = PlanTier.FREE
    status: str = 'active'  # active, expired, cancelled
    start_date: datetime
    expiry_date: datetime | None = None  # None = free (no expiry)
    broadcast_enabled: bool = False
    max_broadcasts_per_day: int = 0
    max_recipients_per_broadcast: int = 0
    max_connected_chats: int = 3
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "Subscription":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
