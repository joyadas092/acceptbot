from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

class ChatRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db['chats']
        self.admins_collection = db['chat_admins']
        self.settings_collection = db['chat_settings']

    async def upsert_chat(self, chat_data: Dict[str, Any]) -> Dict[str, Any]:
        chat_id = chat_data['chat_id']
        now = datetime.now(timezone.utc)
        
        update_doc = {
            "$set": {k: v for k, v in chat_data.items() if k != 'chat_id'},
            "$setOnInsert": {"created_at": now, "total_join_requests": 0, "total_approved": 0, "total_welcome_sent": 0}
        }
        
        return await self.collection.find_one_and_update(
            {"chat_id": chat_id},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def get_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"chat_id": chat_id})

    async def get_chats_by_connected_user(self, user_id: int) -> List[Dict[str, Any]]:
        admin_records = await self.admins_collection.find({"user_id": user_id}).to_list(length=None)
        chat_ids = [record['chat_id'] for record in admin_records]
        if not chat_ids:
            return []
        return await self.collection.find({"chat_id": {"$in": chat_ids}}).to_list(length=None)

    async def get_all_active(self) -> List[Dict[str, Any]]:
        return await self.collection.find({"status": "active"}).to_list(length=None)

    async def update_status(self, chat_id: int, status: str) -> bool:
        result = await self.collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def update_permissions(self, chat_id: int, permissions: Dict[str, Any], has_permission: bool) -> bool:
        result = await self.collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"permissions": permissions, "has_permission": has_permission, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def increment_counter(self, chat_id: int, field: str, amount: int = 1) -> None:
        await self.collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {field: amount}}
        )

    async def count_total(self) -> int:
        return await self.collection.count_documents({})

    async def count_by_type(self, chat_type: str) -> int:
        return await self.collection.count_documents({"chat_type": chat_type})

    async def count_by_status(self, status: str) -> int:
        return await self.collection.count_documents({"status": status})

    # --- Admin management ---
    async def upsert_admin(self, chat_id: int, user_id: int) -> None:
        await self.admins_collection.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True
        )

    async def remove_admin(self, chat_id: int, user_id: int) -> None:
        await self.admins_collection.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def get_admins(self, chat_id: int) -> List[Dict[str, Any]]:
        return await self.admins_collection.find({"chat_id": chat_id}).to_list(length=None)

    async def is_admin(self, chat_id: int, user_id: int) -> bool:
        record = await self.admins_collection.find_one({"chat_id": chat_id, "user_id": user_id})
        return record is not None

    # --- Settings ---
    async def get_settings(self, chat_id: int) -> Optional[Dict[str, Any]]:
        return await self.settings_collection.find_one({"chat_id": chat_id})

    async def upsert_settings(self, chat_id: int, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        update_doc = {
            "$set": {k: v for k, v in settings_data.items() if k != 'chat_id'},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        }
        return await self.settings_collection.find_one_and_update(
            {"chat_id": chat_id},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def update_settings_field(self, chat_id: int, field: str, value: Any) -> bool:
        result = await self.settings_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {field: value, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def get_settings_with_defaults(self, chat_id: int) -> Dict[str, Any]:
        settings = await self.get_settings(chat_id)
        if settings:
            return settings
        
        return {
            "chat_id": chat_id,
            "auto_approve": False,
            "welcome_message_enabled": False,
            "welcome_message_text": "Welcome to the group!",
            "delay_seconds": 0
        }
