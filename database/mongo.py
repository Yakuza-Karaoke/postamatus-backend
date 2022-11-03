from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from database.models import PointInfo, UserDataReg

class _MongoWrapper:
    def __init__(self, url: str) -> None:
        self.db: AsyncIOMotorDatabase = AsyncIOMotorClient(url)['db']

        self.points_collection: AsyncIOMotorCollection = self.db['points']
        self.users_collection: AsyncIOMotorCollection = self.db['users']

    async def get_all_points(self) -> dict:
        pass

    async def add_points(self, point: list[PointInfo]) -> None:
        await self.points_collection.insert_many([p.dict() for p in point])

    async def register_user(self, user_data: UserDataReg) -> None:
        if await self.find_user(username=user_data.username, password=user_data.password):
            raise ValueError
        return await self.users_collection.insert_one(user_data.dict())

    async def find_user_by_username(self, username: str) -> dict | None:
        return await self.users_collection.find({'username': username}).to_list(length=None)

    async def find_user(self, username: str, password: str) -> dict | None:
        return await self.users_collection.find({'username': username, 'password': password}).to_list(length=None)
        
    async def get_all_users(self) -> list[dict]:
        return await self.users_collection.find({}, {'password': 0}).to_list(length=None)

Mongo = _MongoWrapper(url='mongodb://root:root@mongo:27017')