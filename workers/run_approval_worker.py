"""
Approval Worker Entry Point

Run this as a separate process:
    python workers/run_approval_worker.py

This process handles:
- Delayed join request approvals
- Delayed welcome messages
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
from app.workers.approval_worker import ApprovalWorker
# Mocks/imports for services would be here. Assuming they exist in app.services
# from app.services.approval_service import ApprovalService
# from app.services.welcome_service import WelcomeService
from unittest.mock import AsyncMock

async def main():
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger('run_approval_worker')
    
    logger.info("Initializing Approval Worker Process...")
    
    # Connect DB
    await db_manager.connect(settings.MONGODB_URI, settings.MONGODB_DB_NAME)
    
    # Connect Redis
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    # Instantiate services
    # approval_service = ApprovalService(db_manager.db, redis_client)
    # welcome_service = WelcomeService(db_manager.db, redis_client)
    approval_service = AsyncMock() # Replace with actual service instantiation
    welcome_service = AsyncMock()
    
    worker = ApprovalWorker(
        approval_service=approval_service,
        welcome_service=welcome_service,
        poll_interval=settings.APPROVAL_POLL_INTERVAL
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
        
    logger.info("Starting Approval Worker...")
    worker_task = asyncio.create_task(worker.start())
    
    await stop_event.wait()
    await worker_task
    
    # Cleanup
    await redis_client.aclose()
    await db_manager.disconnect()
    logger.info("Approval Worker Process shut down successfully.")

if __name__ == '__main__':
    # Fix for Windows signal handling in asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
