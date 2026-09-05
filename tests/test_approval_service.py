import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

class DuplicateKeyError(Exception):
    pass
    
class TelegramBadRequest(Exception):
    pass

class ApprovalService:
    def __init__(self, jr_repo, chat_repo, telegram_service, redis):
        self.jr_repo = jr_repo
        self.chat_repo = chat_repo
        self.telegram = telegram_service
        self.redis = redis
        
    async def handle_new_join_request(self, chat_id, user_id, settings):
        if not settings.get("auto_approval_enabled", False):
            return None
            
        delay = settings.get("approval_delay_seconds", 0)
        
        try:
            if delay == 0:
                await self.execute_approval(chat_id, user_id)
                return "approved"
            else:
                scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                await self.jr_repo.create({"chat_id": chat_id, "user_id": user_id, "scheduled_at": scheduled_at, "status": "scheduled"})
                return "scheduled"
        except DuplicateKeyError:
            return "ignored"
            
    async def execute_approval(self, chat_id, user_id):
        lock_name = f"lock:approve:{chat_id}:{user_id}"
        async with self.redis.lock(lock_name, timeout=10):
            req = await self.jr_repo.get(chat_id, user_id)
            if req and req.get("status") == "approved":
                return "already_approved"
                
            try:
                await self.telegram.approve_join_request(chat_id, user_id)
                await self.jr_repo.update_status(chat_id, user_id, "approved")
                return "approved"
            except TelegramBadRequest:
                await self.jr_repo.update_status(chat_id, user_id, "failed")
                return "failed"
                
    async def process_due_requests(self):
        due = await self.jr_repo.get_due_requests()
        count = 0
        for req in due:
            chat = await self.chat_repo.get(req["chat_id"])
            if not chat or chat.get("status") != "active":
                continue
            await self.execute_approval(req["chat_id"], req["user_id"])
            count += 1
        return count


@pytest.fixture
def approval_service(mock_join_request_repo, mock_chat_repo, mock_telegram_service, mock_redis):
    return ApprovalService(mock_join_request_repo, mock_chat_repo, mock_telegram_service, mock_redis)

@pytest.mark.asyncio
async def test_immediate_approval(approval_service, mock_telegram_service):
    settings = {"auto_approval_enabled": True, "approval_delay_seconds": 0}
    res = await approval_service.handle_new_join_request(-100, 123, settings)
    assert res == "approved"
    mock_telegram_service.approve_join_request.assert_called_once_with(-100, 123)

@pytest.mark.asyncio
async def test_delayed_approval_schedules(approval_service, mock_join_request_repo):
    settings = {"auto_approval_enabled": True, "approval_delay_seconds": 60}
    res = await approval_service.handle_new_join_request(-100, 123, settings)
    assert res == "scheduled"
    mock_join_request_repo.create.assert_called_once()
    args = mock_join_request_repo.create.call_args[0][0]
    assert args["status"] == "scheduled"
    assert args["scheduled_at"] is not None

@pytest.mark.asyncio
async def test_disabled_approval_does_nothing(approval_service):
    settings = {"auto_approval_enabled": False}
    res = await approval_service.handle_new_join_request(-100, 123, settings)
    assert res is None

@pytest.mark.asyncio
async def test_duplicate_request_ignored(approval_service, mock_join_request_repo):
    mock_join_request_repo.create.side_effect = DuplicateKeyError("dup")
    settings = {"auto_approval_enabled": True, "approval_delay_seconds": 60}
    res = await approval_service.handle_new_join_request(-100, 123, settings)
    assert res == "ignored"

@pytest.mark.asyncio
async def test_execute_approval_locks_redis(approval_service, mock_redis, mock_telegram_service):
    await approval_service.execute_approval(-100, 123)
    mock_redis.lock.assert_called_with("lock:approve:-100:123", timeout=10)

@pytest.mark.asyncio
async def test_already_approved_request_not_reprocessed(approval_service, mock_join_request_repo, mock_telegram_service):
    mock_join_request_repo.get.return_value = {"status": "approved"}
    res = await approval_service.execute_approval(-100, 123)
    assert res == "already_approved"
    mock_telegram_service.approve_join_request.assert_not_called()

@pytest.mark.asyncio
async def test_missing_permission_fails_gracefully(approval_service, mock_telegram_service, mock_join_request_repo):
    mock_join_request_repo.get.return_value = {"status": "pending"}
    mock_telegram_service.approve_join_request.side_effect = TelegramBadRequest("not admin")
    res = await approval_service.execute_approval(-100, 123)
    assert res == "failed"
    mock_join_request_repo.update_status.assert_called_with(-100, 123, "failed")

@pytest.mark.asyncio
async def test_process_due_requests_returns_count(approval_service, mock_join_request_repo, mock_chat_repo):
    mock_join_request_repo.get_due_requests.return_value = [{"chat_id": -100, "user_id": 1}, {"chat_id": -100, "user_id": 2}]
    mock_chat_repo.get.return_value = {"status": "active"}
    
    with patch.object(approval_service, 'execute_approval', new_callable=AsyncMock) as mock_exec:
        count = await approval_service.process_due_requests()
        assert count == 2
        assert mock_exec.call_count == 2

@pytest.mark.asyncio
async def test_cancelled_chat_skipped(approval_service, mock_join_request_repo, mock_chat_repo):
    mock_join_request_repo.get_due_requests.return_value = [{"chat_id": -100, "user_id": 1}]
    mock_chat_repo.get.return_value = {"status": "disconnected"}
    
    with patch.object(approval_service, 'execute_approval', new_callable=AsyncMock) as mock_exec:
        count = await approval_service.process_due_requests()
        assert count == 0
        mock_exec.assert_not_called()
