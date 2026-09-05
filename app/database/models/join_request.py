from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class JoinRequestStatus(str, Enum):
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    APPROVED = 'approved'
    DECLINED = 'declined'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class WelcomeStatus(str, Enum):
    NOT_SENT = 'not_sent'
    SENT = 'sent'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    SCHEDULED = 'scheduled'

class JoinRequest(BaseModel):
    id: str  # generated
    chat_id: int
    user_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    bio: str | None = None
    invite_link: str | None = None
    status: JoinRequestStatus = JoinRequestStatus.PENDING
    scheduled_at: datetime | None = None
    approved_at: datetime | None = None
    welcome_status: WelcomeStatus = WelcomeStatus.NOT_SENT
    welcome_sent_at: datetime | None = None
    welcome_scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    def to_mongo(self) -> dict:
        # Convert enums to string values
        data = self.model_dump()
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "JoinRequest":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
