"""
RequestAcceptBot — Main Entry Point

Modes:
- Production: Webhook mode (ENVIRONMENT=production)
- Development: Long polling mode (ENVIRONMENT=development)
"""
import asyncio
import sys
import signal
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.connection import db_manager
from app.database.repositories import (
    UserRepository, ChatRepository, JoinRequestRepository,
    BroadcastRepository, SubscriptionRepository
)
from app.bot.middlewares.database import DatabaseMiddleware
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.bot.handlers import setup_routers


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger('main')

    # Connect DB and Redis
    await db_manager.connect(settings.mongodb_uri, settings.mongodb_database)
    await db_manager.create_indexes()
    db = db_manager.db

    redis_client = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis_client)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode='HTML'))
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""

    dp = Dispatcher(storage=storage)

    # Inject shared data
    dp['settings'] = settings
    dp['bot_username'] = bot_username

    # Register middlewares
    db_middleware = DatabaseMiddleware(
        db=db,
        user_repo_class=UserRepository,
        chat_repo_class=ChatRepository,
        join_request_repo_class=JoinRequestRepository,
        broadcast_repo_class=BroadcastRepository,
        subscription_repo_class=SubscriptionRepository,
    )
    dp.update.outer_middleware(db_middleware)
    dp.update.outer_middleware(AuthMiddleware(settings.super_admin_ids))
    dp.update.middleware(ThrottlingMiddleware(redis_client))
    dp.update.middleware(LoggingMiddleware())

    # Register all routers
    main_router = setup_routers()
    dp.include_router(main_router)

    if settings.is_production:
        webhook_url = f"{settings.webhook_url}{settings.webhook_path}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.webhook_secret,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info("Webhook set", url=webhook_url)

        app = web.Application()
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.webhook_secret,
        )
        webhook_handler.register(app, path=settings.webhook_path)
        app.router.add_get('/health', health_check)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=settings.app_port)
        logger.info(f"Starting webhook server on 0.0.0.0:{settings.app_port}")
        await site.start()

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass
        await stop_event.wait()
        await runner.cleanup()
    else:
        logger.info("Starting long polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    await bot.session.close()
    await redis_client.aclose()
    await db_manager.disconnect()


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
        sys.exit(1)
