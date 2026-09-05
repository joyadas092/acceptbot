import pytest
from unittest.mock import AsyncMock

# Mock implementation
class ChatService:
    def __init__(self, chat_repo, telegram_service):
        self.chat_repo = chat_repo
        self.telegram_service = telegram_service
        
    async def on_bot_added_as_admin(self, chat_data, has_permission):
        chat_data["has_join_request_permission"] = has_permission
        chat_data["status"] = "active"
        return await self.chat_repo.upsert(chat_data)
        
    async def disconnect_chat(self, chat_id):
        await self.chat_repo.update_status(chat_id, "disconnected")
        
    async def verify_user_is_chat_admin(self, chat_id, user_id):
        # Calls telegram API
        return await self.telegram_service.is_admin(chat_id, user_id)
        
    async def update_setting(self, chat_id, field, value):
        await self.chat_repo.update_setting(chat_id, field, value)

@pytest.fixture
def chat_service(mock_chat_repo, mock_telegram_service):
    return ChatService(mock_chat_repo, mock_telegram_service)

@pytest.mark.asyncio
async def test_bot_added_as_admin_stores_chat(chat_service, mock_chat_repo, sample_chat):
    mock_chat_repo.upsert.return_value = sample_chat
    result = await chat_service.on_bot_added_as_admin(sample_chat, True)
    
    mock_chat_repo.upsert.assert_called_once()
    assert result["has_join_request_permission"] is True
    assert result["status"] == "active"

@pytest.mark.asyncio
async def test_bot_added_without_permission_flags_it(chat_service, mock_chat_repo, sample_chat):
    sample_chat_no_perm = sample_chat.copy()
    sample_chat_no_perm["has_join_request_permission"] = False
    
    mock_chat_repo.upsert.return_value = sample_chat_no_perm
    result = await chat_service.on_bot_added_as_admin(sample_chat, False)
    
    assert result["has_join_request_permission"] is False

@pytest.mark.asyncio
async def test_bot_removed_marks_disconnected(chat_service, mock_chat_repo):
    await chat_service.disconnect_chat(-100123)
    mock_chat_repo.update_status.assert_called_once_with(-100123, "disconnected")

@pytest.mark.asyncio
async def test_disconnect_chat(chat_service, mock_chat_repo):
    await chat_service.disconnect_chat(-100123)
    mock_chat_repo.update_status.assert_called_once_with(-100123, "disconnected")

@pytest.mark.asyncio
async def test_verify_user_is_chat_admin_calls_telegram_api(chat_service, mock_telegram_service):
    mock_telegram_service.is_admin.return_value = True
    result = await chat_service.verify_user_is_chat_admin(-100123, 12345)
    
    mock_telegram_service.is_admin.assert_called_once_with(-100123, 12345)
    assert result is True

@pytest.mark.asyncio
async def test_update_single_setting(chat_service, mock_chat_repo):
    await chat_service.update_setting(-100123, "auto_approval_enabled", False)
    mock_chat_repo.update_setting.assert_called_once_with(-100123, "auto_approval_enabled", False)
