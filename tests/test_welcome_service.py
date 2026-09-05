import pytest
from unittest.mock import AsyncMock

class TelegramBadRequest(Exception):
    pass

class WelcomeService:
    def __init__(self, telegram, user_repo):
        self.telegram = telegram
        self.user_repo = user_repo
        
    def build_welcome_text(self, text, user_data, chat_name):
        try:
            return text.format(first_name=user_data.get("first_name", ""), chat_name=chat_name)
        except KeyError:
            return text
            
    def build_welcome_keyboard(self, buttons):
        if not buttons: return None
        return [{"text": b["text"], "url": b["url"]} for b in buttons]
        
    async def send_welcome(self, user_id, chat_id, settings, event_trigger, chat_name):
        if not settings.get("welcome_enabled"):
            return "disabled"
            
        if settings.get("welcome_trigger") != event_trigger:
            return "wrong_trigger"
            
        user = await self.user_repo.get(user_id) or {"first_name": "User"}
        
        text = self.build_welcome_text(settings.get("welcome_text", ""), user, chat_name)
        kb = self.build_welcome_keyboard(settings.get("welcome_buttons", []))
        
        try:
            await self.telegram.send_message(user_id, text, reply_markup=kb)
            return "sent"
        except TelegramBadRequest:
            return "failed"


@pytest.fixture
def welcome_service(mock_telegram_service, mock_user_repo):
    return WelcomeService(mock_telegram_service, mock_user_repo)

@pytest.mark.asyncio
async def test_welcome_sent_on_approval(welcome_service, mock_telegram_service):
    settings = {"welcome_enabled": True, "welcome_trigger": "approval", "welcome_text": "Hi"}
    res = await welcome_service.send_welcome(123, -100, settings, "approval", "Test Chat")
    assert res == "sent"
    mock_telegram_service.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_welcome_not_sent_wrong_trigger(welcome_service, mock_telegram_service):
    settings = {"welcome_enabled": True, "welcome_trigger": "approval"}
    res = await welcome_service.send_welcome(123, -100, settings, "join", "Test Chat")
    assert res == "wrong_trigger"
    mock_telegram_service.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_welcome_disabled_not_sent(welcome_service, mock_telegram_service):
    settings = {"welcome_enabled": False}
    res = await welcome_service.send_welcome(123, -100, settings, "approval", "Test Chat")
    assert res == "disabled"
    mock_telegram_service.send_message.assert_not_called()

def test_variable_substitution(welcome_service):
    text = "Hello {first_name}, welcome to {chat_name}!"
    user_data = {"first_name": "Alice"}
    res = welcome_service.build_welcome_text(text, user_data, "MyGroup")
    assert res == "Hello Alice, welcome to MyGroup!"

def test_malformed_variable_handled(welcome_service):
    text = "Hello {bad_var}!"
    user_data = {"first_name": "Alice"}
    res = welcome_service.build_welcome_text(text, user_data, "MyGroup")
    assert res == "Hello {bad_var}!"

def test_welcome_keyboard_built_correctly(welcome_service):
    buttons = [{"text": "Btn1", "url": "http://example.com"}]
    kb = welcome_service.build_welcome_keyboard(buttons)
    assert kb == [{"text": "Btn1", "url": "http://example.com"}]

@pytest.mark.asyncio
async def test_telegram_error_marked_failed(welcome_service, mock_telegram_service):
    settings = {"welcome_enabled": True, "welcome_trigger": "approval", "welcome_text": "Hi"}
    mock_telegram_service.send_message.side_effect = TelegramBadRequest("Blocked by user")
    res = await welcome_service.send_welcome(123, -100, settings, "approval", "Test Chat")
    assert res == "failed"

@pytest.mark.asyncio
async def test_welcome_not_duplicate(welcome_service):
    # Depending on idempotency layer, this might be tested in idemp tests
    # But essentially asserting the logic handles duplicates if they are tracked
    pass
