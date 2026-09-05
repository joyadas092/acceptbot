from datetime import datetime
from pydantic import BaseModel

class Plan(BaseModel):
    plan_id: str
    name: str
    tier: str
    price_usd: float = 0.0
    duration_days: int | None = None  # None = lifetime
    broadcast_enabled: bool
    max_broadcasts_per_day: int
    max_recipients_per_broadcast: int
    max_connected_chats: int
    features: list[str] = []
    is_active: bool = True
    created_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "Plan":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
