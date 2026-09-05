import asyncio
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class AuthMiddleware(BaseMiddleware):
    """
    Injects `is_super_admin: bool` into handler data.
    Also registers/updates user on every private message.
    """
    def __init__(self, settings, user_service):
        self.settings = settings
        self.user_service = user_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if user and not user.is_bot:
            is_super_admin = user.id in self.settings.super_admin_id_list
            data['is_super_admin'] = is_super_admin
            
            # Register/update user in background
            username = user.username
            first_name = user.first_name
            last_name = user.last_name
            language_code = user.language_code
            
            asyncio.create_task(
                self.user_service.register_or_update_user(
                    user_id=user.id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code
                )
            )
            
        return await handler(event, data)
