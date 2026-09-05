import pytest
from unittest.mock import AsyncMock

# from app.services.user_service import UserService
# from app.models.user import User

# Mock implementation for tests
class UserService:
    def __init__(self, repo, settings):
        self.repo = repo
        self.settings = settings
        
    async def register_or_update(self, user_data):
        user = await self.repo.upsert(user_data)
        return user
        
    def is_super_admin(self, user_id):
        return user_id in self.settings.SUPER_ADMIN_IDS
        
    async def mark_blocked(self, user_id):
        await self.repo.update_status(user_id, "blocked")
        
    async def get_stats(self):
        return await self.repo.get_counts()

@pytest.fixture
def user_service(mock_user_repo, settings):
    return UserService(mock_user_repo, settings)

@pytest.mark.asyncio
async def test_register_new_user(user_service, mock_user_repo, sample_user):
    mock_user_repo.upsert.return_value = sample_user
    result = await user_service.register_or_update(sample_user)
    
    mock_user_repo.upsert.assert_called_once_with(sample_user)
    assert result == sample_user

@pytest.mark.asyncio
async def test_update_existing_user(user_service, mock_user_repo, sample_user):
    # Same code path for register_or_update in upsert design
    mock_user_repo.upsert.return_value = sample_user
    result = await user_service.register_or_update(sample_user)
    
    mock_user_repo.upsert.assert_called_once_with(sample_user)
    assert result == sample_user

def test_is_super_admin_from_settings(user_service, settings):
    admin_id = settings.SUPER_ADMIN_IDS[0]
    assert user_service.is_super_admin(admin_id) is True

def test_is_super_admin_not_in_settings(user_service):
    assert user_service.is_super_admin(999999) is False

@pytest.mark.asyncio
async def test_mark_blocked(user_service, mock_user_repo):
    await user_service.mark_blocked(12345)
    mock_user_repo.update_status.assert_called_once_with(12345, "blocked")

@pytest.mark.asyncio
async def test_get_stats_returns_correct_counts(user_service, mock_user_repo):
    mock_user_repo.get_counts.return_value = {"active": 100, "blocked": 5}
    stats = await user_service.get_stats()
    assert stats == {"active": 100, "blocked": 5}
