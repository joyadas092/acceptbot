from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db['users']

    async def upsert(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        telegram_id = user_data['telegram_id']
        now = datetime.now(timezone.utc)
        
        update_doc = {
            "$set": {k: v for k, v in user_data.items() if k != 'telegram_id'},
            "$setOnInsert": {"created_at": now}
        }
        
        return await self.collection.find_one_and_update(
            {"telegram_id": telegram_id},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"telegram_id": telegram_id})

    async def update_status(self, telegram_id: int, status: str) -> bool:
        result = await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def count_total(self) -> int:
        return await self.collection.count_documents({})

    async def count(self) -> int:
        return await self.count_total()

    async def count_by_status(self, status: str) -> int:
        return await self.collection.count_documents({"status": status})

    async def count_new_since(self, since: datetime) -> int:
        return await self.collection.count_documents({"created_at": {"$gte": since}})

    async def get_all_eligible_for_broadcast(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"status": "active"}).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def mark_last_seen(self, telegram_id: int) -> None:
        await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"last_seen": datetime.now(timezone.utc)}}
        )

    async def set_super_admin(self, telegram_id: int, value: bool) -> bool:
        result = await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"is_super_admin": value}}
        )
        return result.modified_count > 0
