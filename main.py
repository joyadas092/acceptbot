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
from app.bot.handlers import setup_routers
from app.bot.middlewares import AuthMiddleware, DatabaseMiddleware, LoggingMiddleware, ThrottlingMiddleware
from app.database.repositories import (
    UserRepository, ChatRepository, JoinRequestRepository,
    BroadcastRepository, SubscriptionRepository,
)
from app.services.user_service import UserService
from app.services.rate_limiter import UserCommandThrottler

async def on_startup(bot: Bot, settings, db_manager, redis_client) -> None:
    """Called on bot startup."""
    logger = get_logger('startup')
    logger.info("Starting bot...")

    # Connect DB
    await db_manager.connect(settings.mongodb_uri, settings.mongodb_database)
    # Create indexes could be called here
    # await db_manager.create_indexes()

    if settings.environment == "production" and settings.webhook_host:
        webhook_url = f"{settings.webhook_host}{settings.webhook_path}"
        if settings.webhook_secret:
            await bot.set_webhook(url=webhook_url, secret_token=settings.webhook_secret)
        else:
            await bot.set_webhook(url=webhook_url)
        logger.info("Webhook set", url=webhook_url)

    logger.info("Bot started successfully")

async def on_shutdown(bot: Bot, settings, db_manager, redis_client) -> None:
    """Called on shutdown."""
    logger = get_logger('shutdown')
    logger.info("Shutting down bot...")

    if settings.environment == "production":
        try:
            await bot.delete_webhook()
        except Exception:
            pass
        logger.info("Webhook deleted")

    await db_manager.disconnect()
    try:
        await redis_client.aclose()
    except Exception:
        pass
    logger.info("Bot shutdown complete")

async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger('main')

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode='HTML'))

    redis_client = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage)

    # Register dependencies in kwargs
    dp['settings'] = settings
    dp['db_manager'] = db_manager
    dp['redis_client'] = redis_client

    # Build services used by middlewares
    user_service = UserService()

    # Register middlewares (order matters: outer first)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware(UserCommandThrottler(redis_client)))
    dp.callback_query.middleware(ThrottlingMiddleware(UserCommandThrottler(redis_client)))
    dp.message.middleware(AuthMiddleware(settings, user_service))
    dp.callback_query.middleware(AuthMiddleware(settings, user_service))

    # Routers
    main_router = setup_routers()
    dp.include_router(main_router)

    dp.startup.register(lambda bot: on_startup(bot, settings, db_manager, redis_client))
    dp.shutdown.register(lambda bot: on_shutdown(bot, settings, db_manager, redis_client))

    if settings.environment == "production":
        app = web.Application()

        # Webhook handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.webhook_secret,
        )
        webhook_requests_handler.register(app, path=settings.webhook_path)

        # Health check
        app.router.add_get('/health', health_check)

        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=settings.app_port)

        logger.info(f"Starting web server on 0.0.0.0:{settings.app_port}")
        await site.start()

        # Run forever
        stop_event = asyncio.Event()

        def handle_signal():
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, handle_signal)
            except NotImplementedError:
                pass  # Windows

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
