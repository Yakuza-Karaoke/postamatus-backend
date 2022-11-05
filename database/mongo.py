from .exceptions import SamePassword, UserNotFound
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from database.models import PointInfo, UserDataReg


class _MongoWrapper:
    def __init__(self, url: str) -> None:
        self.db: AsyncIOMotorDatabase = AsyncIOMotorClient(url)["db"]

        self.points_collection: AsyncIOMotorCollection = self.db["points"]
        self.users_collection: AsyncIOMotorCollection = self.db["users"]

    async def find_close_points(self, lat: float, long: float, distance: int = 500) -> list[dict]:
        return await self.points_collection.aggregate(
            [
                {
                    "$geoNear": {
                        "near": {"type": "Point", "coordinates": [long, lat]},
                        "spherical": False,
                        "distanceField": "calcDistance",
                        "query": { "type": "house" },
                        "maxDistance": distance,
                        "minDistance": 0,
                    }
                },
                {"$unset": ["_id"]},
                {"$sort": {"calcDistance": 1}},
            ]
        ).to_list(length=None)

    async def calculate_point_score(self, lat: float, long: float, distance: int = 500, coeff: int = 50) -> dict:
        """
        По данным координатам посчитать оценку точки в зависимости от ближайших зданий
        Возвращаем все точки и оценку данной

        Пример ближайшей точки:
        {
            "address": "улица Кировоградская 42к1",
            "population": 57,
            "location": {
                "type": "Point",
                "coordinates": [
                    37.598054392087334,
                    55.6014346
                ]
            },
            "type": "house",
            "calcDistance": 201.18500008983796
        },
        """
        points = await self.find_close_points(lat, long, distance)
        response: dict[str, Any] = {"near": points}
        # TODO: посчитать score от 0 до 100
        score = 0
        for house in points:
            population = house['population']
            dist = (house['calcDistance'] > coeff if house['calcDistance'] else coeff)
            score += population * coeff / dist
        response["point"] = {"score": score, "coords": [lat, long]}
        return response

    async def add_points(self, point: list[PointInfo]) -> None:
        await self.points_collection.insert_many([p.dict() for p in point])

    async def register_user(self, user_data: UserDataReg) -> None:
        if await self.find_user(username=user_data.username, password=user_data.password):
            raise ValueError
        return await self.users_collection.insert_one(user_data.dict())

    async def find_user_by_username(self, username: str) -> dict | None:
        return await self.users_collection.find({"username": username}).to_list(length=None)

    async def find_user(self, username: str, password: str) -> dict | None:
        return await self.users_collection.find({"username": username, "password": password}).to_list(length=None)

    async def edit_password(self, username: str, password: str, new_password: str) -> None:
        if await self.users_collection.find({"username": username, "password": password}).to_list(length=None):
            if (password == new_password):
                raise SamePassword()
            await self.users_collection.update_one({"username" : username}, {"$set": {"password" : new_password}})
        else:
            raise UserNotFound()
        return None


    async def get_all_users(self) -> list[dict]:
        return await self.users_collection.find({}, {"password": 0}).to_list(length=None)


Mongo = _MongoWrapper(url="mongodb://root:root@178.170.192.207:27017")
