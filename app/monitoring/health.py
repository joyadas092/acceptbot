from aiohttp import web
from datetime import datetime, timezone

async def health_check(request):
    return web.json_response({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def ready_check(request):
    db_manager = request.app['db_manager']
    redis_client = request.app['redis_client']
    
    try:
        # Check MongoDB
        if db_manager.client:
            await db_manager.client.admin.command('ping')
        else:
            raise Exception("MongoDB client not initialized")
            
        # Check Redis
        if redis_client:
            await redis_client.ping()
        else:
            raise Exception("Redis client not initialized")
            
        return web.json_response({
            "status": "ready",
            "mongodb": "ok",
            "redis": "ok"
        })
    except Exception as e:
        return web.json_response({
            "status": "error",
            "message": str(e)
        }, status=503)

def create_health_app(db_manager, redis_client) -> web.Application:
    app = web.Application()
    app['db_manager'] = db_manager
    app['redis_client'] = redis_client
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/ready', ready_check)
    
    return app
