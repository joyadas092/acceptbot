"""
Broadcast Worker Entry Point

Run this as a separate process:
    python workers/run_broadcast_worker.py
"""
import asyncio
import sys
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.connection import db_manager
from redis.asyncio import Redis
from app.workers.broadcast_worker import BroadcastWorker
from unittest.mock import AsyncMock

async def main():
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger('run_broadcast_worker')
    
    logger.info("Initializing Broadcast Worker Process...")
    
    # Connect DB
    await db_manager.connect(settings.MONGODB_URI, settings.MONGODB_DB_NAME)
    
    # Connect Redis
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    # Instantiate services
    broadcast_service = AsyncMock()
    broadcast_repo = AsyncMock()
    telegram_service = AsyncMock()
    rate_limiter = AsyncMock()
    
    worker = BroadcastWorker(
        broadcast_service=broadcast_service,
        broadcast_repo=broadcast_repo,
        telegram_service=telegram_service,
        rate_limiter=rate_limiter,
        batch_size=200,
        poll_interval=10
    )
    
    # Graceful shutdown handler
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def handle_signal(sig):
        logger.info(f"Received exit signal {sig.name}...")
        asyncio.create_task(worker.stop())
        stop_event.set()
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))
        
    logger.info("Starting Broadcast Worker...")
    worker_task = asyncio.create_task(worker.start())
    
    await stop_event.wait()
    await worker_task
    
    # Cleanup
    await redis_client.aclose()
    await db_manager.disconnect()
    logger.info("Broadcast Worker Process shut down successfully.")

if __name__ == '__main__':
    # Fix for Windows signal handling in asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
