import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import time

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    """Structured logging for each update."""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        user = data.get('event_from_user')
        chat = data.get('event_chat')
        
        user_id = user.id if user else None
        chat_id = chat.id if chat else None
        
        event_type = type(event).__name__
        
        logger.debug(f"Received update: {event_type} user_id={user_id} chat_id={chat_id}")
        
        try:
            result = await handler(event, data)
            process_time = time.time() - start_time
            logger.debug(f"Processed update: {event_type} user_id={user_id} chat_id={chat_id} in {process_time:.4f}s")
            return result
        except Exception as e:
            process_time = time.time() - start_time
            logger.exception(f"Error processing update: {event_type} user_id={user_id} chat_id={chat_id} in {process_time:.4f}s: {e}")
            raise
