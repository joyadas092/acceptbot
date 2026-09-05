from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

class SubscriptionRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db['subscriptions']
        self.plans_collection = db['plans']

    async def get_active_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.collection.find_one({
            "user_id": user_id,
            "status": "active",
            "$or": [
                {"expiry_date": None},
                {"expiry_date": {"$gt": now}}
            ]
        })

    async def upsert_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        update_doc = {
            "$set": {k: v for k, v in subscription_data.items() if k != 'user_id'},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        }
        return await self.collection.find_one_and_update(
            {"user_id": user_id},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def get_free_subscription_defaults(self) -> Dict[str, Any]:
        return {
            "plan_id": "FREE",
            "broadcasts_per_day": 0,
            "max_recipients": 0,
            "max_chats": 3
        }

    # Plans
    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        return await self.plans_collection.find_one({"_id": plan_id})

    async def get_all_plans(self) -> List[Dict[str, Any]]:
        return await self.plans_collection.find({}).to_list(length=None)

    async def upsert_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        plan_id = plan_data.get("_id")
        
        update_doc = {
            "$set": {k: v for k, v in plan_data.items() if k != '_id'},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        }
        
        return await self.plans_collection.find_one_and_update(
            {"_id": plan_id},
            update_doc,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def count_by_plan(self, plan_id: str) -> int:
        return await self.collection.count_documents({"plan_id": plan_id})

    async def seed_default_plans(self) -> None:
        now = datetime.now(timezone.utc)
        plans = [
            {
                "_id": "FREE",
                "name": "Free",
                "broadcasts_per_day": 0,
                "max_recipients": 0,
                "max_chats": 3,
                "price": 0.0,
                "created_at": now
            },
            {
                "_id": "PRO",
                "name": "Pro",
                "broadcasts_per_day": 10,
                "max_recipients": 1000,
                "max_chats": 10,
                "price": 9.99,
                "created_at": now
            },
            {
                "_id": "BUSINESS",
                "name": "Business",
                "broadcasts_per_day": 50,
                "max_recipients": 10000,
                "max_chats": -1,  # unlimited
                "price": 29.99,
                "created_at": now
            },
            {
                "_id": "ENTERPRISE",
                "name": "Enterprise",
                "broadcasts_per_day": -1, # unlimited
                "max_recipients": -1, # unlimited
                "max_chats": -1,  # unlimited
                "price": 99.99,
                "created_at": now
            }
        ]
        
        for plan in plans:
            await self.plans_collection.update_one(
                {"_id": plan["_id"]},
                {"$setOnInsert": plan},
                upsert=True
            )
