"""
RequestAcceptBot — Main Entry Point

Modes:
- Production: Webhook mode (ENVIRONMENT=production)
- Development: Long polling mode (ENVIRONMENT=development)
"""
import asyncio
import sys
import signal
from contextlib import asynccontextmanager
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.connection import db_manager

async def on_startup(bot: Bot, settings, db_manager, redis_client) -> None:
    """Called on bot startup."""
    logger = get_logger('startup')
    logger.info("Starting bot...")
    
    # Connect DB
    await db_manager.connect(settings.MONGODB_URI, settings.MONGODB_DB_NAME)
    # Create indexes could be called here
    # await db_manager.create_indexes()
    
    if settings.ENVIRONMENT == "production":
        webhook_url = f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url, secret_token=settings.WEBHOOK_SECRET)
        logger.info("Webhook set", url=webhook_url)
    
    logger.info("Bot started successfully")

async def on_shutdown(bot: Bot, settings, db_manager, redis_client) -> None:
    """Called on shutdown."""
    logger = get_logger('shutdown')
    logger.info("Shutting down bot...")
    
    if settings.ENVIRONMENT == "production":
        await bot.delete_webhook()
        logger.info("Webhook deleted")
        
    await db_manager.disconnect()
    await redis_client.aclose()
    logger.info("Bot shutdown complete")

async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger('main')
    
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    
    redis_client = Redis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage)
    
    # Register dependencies in kwargs
    dp['settings'] = settings
    dp['db_manager'] = db_manager
    dp['redis_client'] = redis_client
    
    # Register routers and middlewares here
    
    dp.startup.register(lambda bot: on_startup(bot, settings, db_manager, redis_client))
    dp.shutdown.register(lambda bot: on_shutdown(bot, settings, db_manager, redis_client))

    if settings.ENVIRONMENT == "production":
        app = web.Application()
        
        # Webhook handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.WEBHOOK_SECRET,
        )
        webhook_requests_handler.register(app, path=settings.WEBHOOK_PATH)
        
        # Health check
        app.router.add_get('/health', health_check)
        
        setup_application(app, dp, bot=bot)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=settings.WEB_PORT)
        
        logger.info(f"Starting web server on 0.0.0.0:{settings.WEB_PORT}")
        await site.start()
        
        # Run forever
        stop_event = asyncio.Event()
        
        def handle_signal():
            stop_event.set()
            
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)
            
        await stop_event.wait()
        await runner.cleanup()
        
    else:
        # Long polling mode
        logger.info("Starting long polling...")
        await bot.delete_webhook()
        await dp.start_polling(bot)
    
if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import logging
        logging.error(f"Fatal error: {e}", exc_info=True)
