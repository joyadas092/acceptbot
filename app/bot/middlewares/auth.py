import asyncio
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class AuthMiddleware(BaseMiddleware):
    """
    Injects `is_super_admin: bool` into handler data.
    Also registers/updates user on every private message.
    """
    def __init__(self, super_admin_ids: list[int]):
        self.super_admin_ids = super_admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if user and not user.is_bot:
            is_super_admin = user.id in self.super_admin_ids
            data['is_super_admin'] = is_super_admin
            
            user_repo = data.get('user_repo')
            if user_repo:
                username = user.username
                first_name = user.first_name
                last_name = user.last_name
                language_code = user.language_code
                
                asyncio.create_task(
                    user_repo.upsert_user(
                        user_id=user.id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        language_code=language_code
                    )
                )
            
        return await handler(event, data)
