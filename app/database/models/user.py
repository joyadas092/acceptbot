from datetime import datetime
from pydantic import BaseModel, Field

class User(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    language_code: str | None = None
    is_bot: bool = False
    status: str = 'active'  # active, blocked, deleted
    is_super_admin: bool = False
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    
    # stats
    total_join_requests: int = 0
    total_chats_connected: int = 0

    def to_mongo(self) -> dict:
        data = self.model_dump()
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "User":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
