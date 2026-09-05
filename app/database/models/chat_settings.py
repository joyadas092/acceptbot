from datetime import datetime
from pydantic import BaseModel

class WelcomeButton(BaseModel):
    text: str
    url: str
    row: int = 0

class ChatSettings(BaseModel):
    chat_id: int
    
    # approval
    auto_approval_enabled: bool = True
    approval_delay_seconds: int = 0  # 0 = immediate
    
    # welcome
    welcome_enabled: bool = True
    welcome_trigger: str = 'on_approval'  # on_request, on_approval, delayed_after_approval
    welcome_delay_seconds: int = 0
    welcome_text: str = 'Welcome {first_name}! Your request has been approved.'
    welcome_buttons: list[WelcomeButton] = []
    welcome_parse_mode: str = 'HTML'
    
    # broadcast
    broadcast_enabled: bool = True
    plan_id: str = 'free'
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict) -> "ChatSettings":
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)
