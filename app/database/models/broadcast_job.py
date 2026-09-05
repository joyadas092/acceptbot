from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class BroadcastStatus(str, Enum):
    DRAFT = 'draft'
    PENDING = 'pending'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class MessagePayload(BaseModel):
    text: str | None = None
    media_type: str | None = None  # photo, video, document, audio, animation, voice
    media_file_id: str | None = None
    caption: str | None = None
    parse_mode: str = 'HTML'
    buttons: list[dict] = []  # [{text, url, row}]

class BroadcastJob(BaseModel):
    job_id: str
    owner_id: int
    chat_id: int | None = None  # None = master broadcast
    target_type: str  # 'chat', 'all_chats', 'master'
    message_payload: MessagePayload
    deduplicate: bool = True
    status: BroadcastStatus = BroadcastStatus.DRAFT
    total_recipients: int = 0
    processed: int = 0
    sent: int = 0
    failed: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "BroadcastJob":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
