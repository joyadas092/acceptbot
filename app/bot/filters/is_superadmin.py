from aiogram.filters import BaseFilter
from aiogram.types import Message

class IsSuperAdmin(BaseFilter):
    """
    Filter that checks if user ID is in settings.super_admin_ids.
    """
    def __init__(self, settings):
        self.settings = settings

    async def __call__(self, message: Message, **data) -> bool:
        user = message.from_user
        return user and user.id in self.settings.super_admin_ids
