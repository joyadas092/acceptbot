from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import time

class ThrottlingMiddleware(BaseMiddleware):
    """
    Per-user rate limiting.
    30 actions per minute default.
    Silently ignores excess updates (no spam response).
    """
    def __init__(self, redis_client, rate: int = 30, per: int = 60):
        self.redis_client = redis_client
        self.rate = rate
        self.per = per

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if user:
            key = f"throttle:{user.id}"
            current = await self.redis_client.get(key)
            if current and int(current) >= self.rate:
                return
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            if not current:
                pipe.expire(key, self.per)
            await pipe.execute()
            
        return await handler(event, data)
