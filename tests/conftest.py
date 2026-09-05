import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from aiogram import Bot

# Assuming the models and settings are defined in the project structure
# from app.models.user import User
# from app.models.chat import Chat, ChatSettings
# from app.models.join_request import JoinRequest
# from app.models.broadcast import BroadcastJob
# from app.config import Settings

@pytest.fixture
def settings():
    class Settings:
        BOT_TOKEN = "123:test"
        MONGODB_URI = "mongodb://localhost:27017"
        MONGODB_DB_NAME = "test_db"
        REDIS_URL = "redis://localhost:6379/0"
        SUPER_ADMIN_IDS = [111111, 222222]
    return Settings()

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.users = AsyncMock()
    db.chats = AsyncMock()
    db.chat_settings = AsyncMock()
    db.join_requests = AsyncMock()
    db.broadcasts = AsyncMock()
    db.subscriptions = AsyncMock()
    return db

@pytest_asyncio.fixture
async def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    
    # Mock for aioredis locks
    class MockLock:
        def __init__(self, name, timeout=None):
            self.name = name
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    redis.lock = MagicMock(side_effect=lambda name, timeout=None: MockLock(name, timeout))
    return redis

@pytest_asyncio.fixture
async def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.id = 123456789
    return bot

@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_chat_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_join_request_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_broadcast_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_subscription_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_telegram_service():
    service = AsyncMock()
    return service

@pytest.fixture
def sample_user():
    return {
        "telegram_id": 12345,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "status": "active",
        "is_super_admin": False
    }

@pytest.fixture
def sample_chat():
    return {
        "chat_id": -1001234567890,
        "title": "Test Group",
        "username": "testgroup",
        "type": "supergroup",
        "connected_by": 12345,
        "status": "active",
        "has_join_request_permission": True
    }

@pytest.fixture
def sample_chat_settings():
    return {
        "chat_id": -1001234567890,
        "auto_approval_enabled": True,
        "approval_delay_seconds": 60,
        "welcome_enabled": True,
        "welcome_trigger": "approval",
        "welcome_delay_seconds": 0,
        "welcome_text": "Welcome {first_name} to {chat_name}!",
        "welcome_buttons": []
    }

@pytest.fixture
def sample_join_request():
    return {
        "id": "req_123",
        "chat_id": -1001234567890,
        "user_id": 98765,
        "status": "pending",
        "scheduled_at": None,
        "welcome_status": "pending"
    }

@pytest.fixture
def sample_broadcast_job():
    return {
        "job_id": "job_123",
        "owner_id": 111111,
        "target_type": "all",
        "message_payload": {"text": "Hello world"},
        "status": "DRAFT",
        "total_recipients": 100,
        "processed": 0,
        "sent": 0,
        "failed": 0
    }
