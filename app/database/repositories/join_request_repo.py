from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

class JoinRequestRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db['join_requests']

    async def create(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        if 'created_at' not in request_data:
            request_data['created_at'] = datetime.now(timezone.utc)
            
        try:
            await self.collection.insert_one(request_data)
            return request_data
        except DuplicateKeyError:
            if '_id' in request_data:
                return await self.get_by_id(request_data['_id'])
            return await self.collection.find_one({
                "chat_id": request_data.get("chat_id"),
                "user_id": request_data.get("user_id")
            })

    async def get_pending(self, chat_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "status": {"$in": ["pending", "scheduled"]}
        })

    async def get_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": request_id})

    async def update_status(self, request_id: str, status: str, extra_fields: Dict[str, Any] = None) -> bool:
        if extra_fields is None:
            extra_fields = {}
        
        update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}
        update_data.update(extra_fields)
        
        result = await self.collection.update_one(
            {"_id": request_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def schedule(self, request_id: str, scheduled_at: datetime) -> bool:
        result = await self.collection.update_one(
            {"_id": request_id},
            {"$set": {
                "status": "scheduled",
                "scheduled_at": scheduled_at,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    async def get_due_scheduled(self, now: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.collection.find({
            "status": "scheduled",
            "scheduled_at": {"$lte": now}
        }).sort("scheduled_at", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def mark_approved(self, request_id: str) -> bool:
        return await self.update_status(request_id, "approved", {"approved_at": datetime.now(timezone.utc)})

    async def mark_welcome_sent(self, request_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": request_id},
            {"$set": {"welcome_sent": True, "welcome_sent_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def mark_welcome_failed(self, request_id: str, reason: str) -> bool:
        result = await self.collection.update_one(
            {"_id": request_id},
            {"$set": {"welcome_sent": False, "welcome_error": reason, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def count_by_status(self, chat_id: int, status: str, since: Optional[datetime] = None) -> int:
        query: Dict[str, Any] = {"chat_id": chat_id, "status": status}
        if since:
            query["created_at"] = {"$gte": since}
        return await self.collection.count_documents(query)

    async def count_pending(self, chat_id: int) -> int:
        return await self.collection.count_documents({
            "chat_id": chat_id,
            "status": {"$in": ["pending", "scheduled"]}
        })

    async def get_recent(self, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"chat_id": chat_id}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_users_for_broadcast(self, chat_id: int, skip: int, limit: int) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": {"chat_id": chat_id, "status": "approved"}},
            {"$group": {"_id": "$user_id"}},
            {"$sort": {"_id": 1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        results = await self.collection.aggregate(pipeline).to_list(length=limit)
        return [{"user_id": r["_id"]} for r in results]
