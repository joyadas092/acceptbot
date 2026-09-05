import asyncio
import random
from typing import Any, Dict
import structlog
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest, TelegramAPIError
from app.core.logging import get_logger

class BroadcastWorker:
    """
    Persistent worker that sends broadcast messages in batches.
    
    Architecture:
    - Polls MongoDB for broadcast_jobs with status=running
    - Processes recipients in configurable batch sizes (default 200)
    - Respects Telegram rate limits via TelegramRateLimiter
    - Handles RetryAfter by sleeping exact duration + jitter
    - Updates progress counters atomically in MongoDB
    - Resumable: skips already-sent recipients (status=sent)
    - One failed recipient never stops the batch
    - Handles job pause: checks status before each batch
    """
    
    def __init__(
        self,
        broadcast_service,
        broadcast_repo,
        telegram_service,
        rate_limiter,
        batch_size: int = 200,
        poll_interval: int = 10
    ):
        self.broadcast_service = broadcast_service
        self.broadcast_repo = broadcast_repo
        self.telegram_service = telegram_service
        self.rate_limiter = rate_limiter
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.running = False
        self.logger = get_logger('broadcast_worker')
    
    async def start(self) -> None:
        """Main worker loop."""
        self.running = True
        self.logger.info('BROADCAST_WORKER_STARTED', poll_interval=self.poll_interval, batch_size=self.batch_size)
        while self.running:
            try:
                await self._process_running_jobs()
            except Exception as e:
                self.logger.error('BROADCAST_WORKER_ERROR', error=str(e), exc_info=True)
            await asyncio.sleep(self.poll_interval)
    
    async def _process_running_jobs(self) -> None:
        """Find and process all running jobs."""
        jobs = await self.broadcast_repo.get_running_jobs()
        for job in jobs:
            if not self.running:
                break
            await self._process_job(job)
    
    async def _process_job(self, job: dict) -> None:
        """Process one batch of recipients for a job."""
        job_id = str(job['_id'])
        # Re-check status before processing
        current_job = await self.broadcast_repo.get_job(job_id)
        if not current_job or current_job.get('status') != 'running':
            return

        recipients = await self.broadcast_repo.get_pending_recipients(job_id, limit=self.batch_size)
        if not recipients:
            await self.broadcast_repo.mark_job_completed(job_id)
            self.logger.info('BROADCAST_JOB_COMPLETED', job_id=job_id)
            return

        success_count = 0
        failure_count = 0

        for recipient in recipients:
            if not self.running:
                break
            
            # Re-check status occasionally or rely on batch size being small enough
            
            success = await self._send_to_recipient(job, recipient)
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            await self.broadcast_repo.update_recipient_status(
                job_id=job_id, 
                user_id=recipient['user_id'], 
                status='sent' if success else 'failed'
            )
            
            # Rate limiting sleep between messages
            await asyncio.sleep(0.04) # 40ms minimum sleep

        await self.broadcast_repo.update_job_progress(job_id, success_count, failure_count)
        self.logger.info('BROADCAST_BATCH_PROCESSED', job_id=job_id, success=success_count, failure=failure_count)
    
    async def _send_to_recipient(self, job: dict, recipient: dict) -> bool:
        """Send broadcast message to one recipient."""
        user_id = recipient['user_id']
        payload = job.get('payload', {})
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Wait based on global rate limiter
                await self.rate_limiter.acquire()
                
                kwargs = await self._build_message_kwargs(payload)
                kwargs['chat_id'] = user_id
                
                if payload.get('type') == 'photo':
                    await self.telegram_service.bot.send_photo(**kwargs)
                elif payload.get('type') == 'video':
                    await self.telegram_service.bot.send_video(**kwargs)
                else:
                    await self.telegram_service.bot.send_message(**kwargs)
                
                return True
                
            except TelegramRetryAfter as e:
                sleep_time = e.retry_after + random.uniform(0.5, 1.5)
                self.logger.warning('RATE_LIMIT_RETRY_AFTER', user_id=user_id, sleep_time=sleep_time)
                await asyncio.sleep(sleep_time)
            except TelegramForbiddenError:
                self.logger.info('USER_BLOCKED_BOT', user_id=user_id)
                return False
            except TelegramBadRequest as e:
                self.logger.warning('BAD_REQUEST', user_id=user_id, error=str(e))
                return False
            except TelegramAPIError as e:
                self.logger.error('TELEGRAM_API_ERROR', user_id=user_id, error=str(e), attempt=attempt)
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                self.logger.error('UNKNOWN_BROADCAST_ERROR', user_id=user_id, error=str(e), exc_info=True)
                return False
                
        return False
    
    async def _build_message_kwargs(self, payload: dict) -> dict:
        """Build kwargs for bot.send_message or send_photo etc."""
        kwargs = {}
        if 'text' in payload:
            kwargs['text'] = payload['text']
        if 'caption' in payload:
            kwargs['caption'] = payload['caption']
        if 'photo' in payload:
            kwargs['photo'] = payload['photo']
        if 'video' in payload:
            kwargs['video'] = payload['video']
        if 'reply_markup' in payload:
            kwargs['reply_markup'] = payload['reply_markup']
        if 'parse_mode' in payload:
            kwargs['parse_mode'] = payload['parse_mode']
        return kwargs
    
    async def stop(self) -> None:
        self.running = False
        self.logger.info('BROADCAST_WORKER_STOPPED')
