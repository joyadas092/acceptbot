from datetime import datetime
from pydantic import BaseModel

class Chat(BaseModel):
    chat_id: int
    title: str
    username: str | None = None
    type: str  # group, supergroup, channel
    connected_by: int  # telegram user_id
    connected_at: datetime
    status: str = 'active'  # active, disconnected, error
    bot_permissions: dict = {}  # stored bot ChatMember permissions
    has_join_request_permission: bool = False
    updated_at: datetime
    
    total_join_requests: int = 0
    total_approved: int = 0
    total_welcome_sent: int = 0

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "Chat":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
