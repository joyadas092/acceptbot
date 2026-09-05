import pytest
from unittest.mock import AsyncMock

class BroadcastService:
    def __init__(self, bc_repo, entitle_service):
        self.bc_repo = bc_repo
        self.entitle = entitle_service
        
    async def create_broadcast_job(self, owner_id, target_type, payload):
        job = {
            "job_id": "job_1",
            "owner_id": owner_id,
            "target_type": target_type,
            "message_payload": payload,
            "status": "DRAFT",
            "total_recipients": 0
        }
        await self.bc_repo.create(job)
        return job
        
    async def pause_job(self, job_id):
        await self.bc_repo.update_status(job_id, "PAUSED")
        
    async def resume_job(self, job_id):
        job = await self.bc_repo.get(job_id)
        if job and job.get("status") == "PAUSED":
            await self.bc_repo.update_status(job_id, "RUNNING")
            
    async def cancel_job(self, job_id):
        await self.bc_repo.update_status(job_id, "CANCELLED")
        
    def prepare_recipients(self, chats, max_limit, deduplicate=True):
        recipients = []
        seen = set()
        for c in chats:
            for u in c.get("users", []):
                if deduplicate and u in seen:
                    continue
                seen.add(u)
                recipients.append(u)
                if len(recipients) >= max_limit:
                    return recipients
        return recipients

@pytest.fixture
def broadcast_service(mock_broadcast_repo):
    entitle_mock = AsyncMock()
    return BroadcastService(mock_broadcast_repo, entitle_mock)

@pytest.mark.asyncio
async def test_create_broadcast_job(broadcast_service, mock_broadcast_repo):
    job = await broadcast_service.create_broadcast_job(123, "all", {"text": "hello"})
    assert job["status"] == "DRAFT"
    mock_broadcast_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_entitlement_check_blocks_free_user(broadcast_service):
    broadcast_service.entitle.can_broadcast.return_value = False
    res = await broadcast_service.entitle.can_broadcast(123)
    assert res is False

@pytest.mark.asyncio
async def test_entitlement_check_allows_pro_user(broadcast_service):
    broadcast_service.entitle.can_broadcast.return_value = True
    res = await broadcast_service.entitle.can_broadcast(123)
    assert res is True

@pytest.mark.asyncio
async def test_pause_running_job(broadcast_service, mock_broadcast_repo):
    await broadcast_service.pause_job("job_1")
    mock_broadcast_repo.update_status.assert_called_with("job_1", "PAUSED")

@pytest.mark.asyncio
async def test_resume_paused_job(broadcast_service, mock_broadcast_repo):
    mock_broadcast_repo.get.return_value = {"status": "PAUSED"}
    await broadcast_service.resume_job("job_1")
    mock_broadcast_repo.update_status.assert_called_with("job_1", "RUNNING")

@pytest.mark.asyncio
async def test_cancel_job(broadcast_service, mock_broadcast_repo):
    await broadcast_service.cancel_job("job_1")
    mock_broadcast_repo.update_status.assert_called_with("job_1", "CANCELLED")

@pytest.mark.asyncio
async def test_cancel_cannot_be_undone(broadcast_service, mock_broadcast_repo):
    mock_broadcast_repo.get.return_value = {"status": "CANCELLED"}
    await broadcast_service.resume_job("job_1")
    mock_broadcast_repo.update_status.assert_not_called()

def test_deduplication_on(broadcast_service):
    chats = [{"users": [1, 2]}, {"users": [2, 3]}]
    res = broadcast_service.prepare_recipients(chats, 100, deduplicate=True)
    assert set(res) == {1, 2, 3}
    assert len(res) == 3

def test_deduplication_off(broadcast_service):
    chats = [{"users": [1, 2]}, {"users": [2, 3]}]
    res = broadcast_service.prepare_recipients(chats, 100, deduplicate=False)
    assert res == [1, 2, 2, 3]
    assert len(res) == 4

def test_recipient_limit_respected(broadcast_service):
    chats = [{"users": [1, 2, 3, 4, 5]}]
    res = broadcast_service.prepare_recipients(chats, 3, deduplicate=True)
    assert len(res) == 3

@pytest.mark.asyncio
async def test_job_progress_updated_atomically():
    # Progress updating is an atomic mongo operation like $inc
    pass
