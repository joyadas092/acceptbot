from typing import Optional, Dict, Any
from aiogram.types import User as AiogramUser

from app.database.repositories import UserRepository
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.utils import utcnow

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo
        self.logger = get_logger('user_service')
        self.settings = get_settings()

    async def register_or_update(self, telegram_user: AiogramUser) -> Dict[str, Any]:
        """
        Called on every /start and update from a user.
        Upserts the user. Returns user dict.
        telegram_user is aiogram User object.
        """
        user_data = {
            "telegram_id": telegram_user.id,
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "language_code": telegram_user.language_code,
            "is_bot": telegram_user.is_bot,
            "is_active": True,
            "last_active_at": utcnow()
        }
        
        user_doc = await self.repo.upsert_user(user_data)
        if not user_doc:
            user_doc = await self.repo.get_by_telegram_id(telegram_user.id)
            
        return user_doc

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return await self.repo.get_by_telegram_id(telegram_id)

    async def mark_blocked(self, telegram_id: int) -> None:
        """Mark user as blocked (bot blocked by user)."""
        await self.repo.update(
            {"telegram_id": telegram_id},
            {"is_active": False, "updated_at": utcnow()}
        )
        self.logger.info(f"User {telegram_id} marked as blocked/inactive.")

    async def mark_active(self, telegram_id: int) -> None:
        await self.repo.update(
            {"telegram_id": telegram_id},
            {"is_active": True, "last_active_at": utcnow(), "updated_at": utcnow()}
        )

    async def is_super_admin(self, telegram_id: int) -> bool:
        """Check against settings.super_admin_id_list — primary check.
           Falls back to DB flag as secondary."""
        if telegram_id in self.settings.super_admin_id_list:
            return True
            
        user = await self.get_user(telegram_id)
        if user and user.get("is_super_admin", False):
            return True
            
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Return total, active, blocked, new_today, new_this_week counts."""
        now = utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # simplistic week calculation
        this_week = today.replace(day=max(1, today.day - today.weekday()))
        
        total = await self.repo.collection.count_documents({})
        active = await self.repo.collection.count_documents({"is_active": True})
        blocked = total - active
        new_today = await self.repo.collection.count_documents({"created_at": {"$gte": today}})
        new_this_week = await self.repo.collection.count_documents({"created_at": {"$gte": this_week}})
        
        return {
            "total": total,
            "active": active,
            "blocked": blocked,
            "new_today": new_today,
            "new_this_week": new_this_week
        }
