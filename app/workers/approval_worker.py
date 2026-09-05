import asyncio
from datetime import datetime, timezone
import structlog
from app.core.logging import get_logger

class ApprovalWorker:
    """
    Persistent worker that processes delayed join request approvals and welcome messages.
    
    Architecture:
    - Polls MongoDB every N seconds for scheduled requests that are due
    - Uses Redis distributed locks to prevent duplicate processing
    - Handles all errors gracefully — one bad request never stops the worker
    - Resumable: if worker restarts, it picks up from MongoDB state
    - MongoDB is the source of truth, Redis only speeds up locking
    """
    
    def __init__(
        self,
        approval_service,
        welcome_service,
        poll_interval: int = 5
    ):
        self.approval_service = approval_service
        self.welcome_service = welcome_service
        self.poll_interval = poll_interval
        self.running = False
        self.logger = get_logger('approval_worker')
    
    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)
    
    async def start(self) -> None:
        """Start the worker loop."""
        self.running = True
        self.logger.info('APPROVAL_WORKER_STARTED', poll_interval=self.poll_interval)
        while self.running:
            try:
                now = self._utcnow()
                # Process due join requests
                approvals_count = await self.approval_service.process_due_requests(now)
                if approvals_count:
                    self.logger.info('APPROVAL_WORKER_PROCESSED_APPROVALS', count=approvals_count)
                
                # Process due welcome messages
                welcomes_count = await self.welcome_service.process_due_welcome_messages(now)
                if welcomes_count:
                    self.logger.info('APPROVAL_WORKER_PROCESSED_WELCOMES', count=welcomes_count)
                    
            except Exception as e:
                self.logger.error('APPROVAL_WORKER_ERROR', error=str(e), exc_info=True)
                # Never crash the worker
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self) -> None:
        """Graceful shutdown."""
        self.running = False
        self.logger.info('APPROVAL_WORKER_STOPPED')
