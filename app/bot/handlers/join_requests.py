from aiogram import Router
from aiogram.types import ChatJoinRequest

router = Router()

@router.chat_join_request()
async def handle_join_request(
    event: ChatJoinRequest,
    join_request_repo,
):
    """
    Main join request handler.
    MUST be fast — offload all processing to services.
    Never await long operations here.
    """
    # For now, just logging to db. 
    # Real logic would use a service to queue auto-approval
    user_id = event.from_user.id
    chat_id = event.chat.id
    
    await join_request_repo.create_request({
        "user_id": user_id,
        "chat_id": chat_id,
        "status": "pending"
    })
    
    # Normally we would dispatch to a celery/arq task or asyncio task to approve after delay
    # We will simulate basic async handoff
