from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class ThrottlingMiddleware(BaseMiddleware):
    """
    Per-user rate limiting.
    30 actions per minute default.
    Silently ignores excess updates (no spam response).
    """
    def __init__(self, throttler):
        self.throttler = throttler

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if user:
            if not await self.throttler.is_allowed(user.id):
                # Don't call handler, don't respond
                return
        return await handler(event, data)
