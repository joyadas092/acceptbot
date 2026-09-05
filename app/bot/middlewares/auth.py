import asyncio
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class AuthMiddleware(BaseMiddleware):
    """
    Injects `is_super_admin: bool` into handler data.
    Also upserts user on every private message update.
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
                asyncio.create_task(
                    _safe_upsert_user(user_repo, user)
                )
        else:
            data.setdefault('is_super_admin', False)

        return await handler(event, data)


async def _safe_upsert_user(user_repo, user) -> None:
    """Upsert user silently — never raises."""
    try:
        await user_repo.upsert({
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name or "",
            "last_name": user.last_name,
            "language_code": getattr(user, "language_code", None),
            "is_bot": False,
            "is_active": True,
        })
    except Exception:
        pass
