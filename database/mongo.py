from .exceptions import SamePassword, UserNotFound, PostamatExist, PostamatsNotFound, PostamatNotExist, NotUsersPostamat
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from database.models import PointInfo, UserDataReg


class _MongoWrapper:
    def __init__(self, url: str) -> None:
        self.db: AsyncIOMotorDatabase = AsyncIOMotorClient(url)["db"]

        self.points_collection: AsyncIOMotorCollection = self.db["points"]
        self.postamatus_collection: AsyncIOMotorCollection = self.db["postamatus"]
        self.users_collection: AsyncIOMotorCollection = self.db["users"]

    async def find_close_points(self, lat: float, long: float, distance: int = 500, type: str = "house" ) -> list[dict]:
        return await self.points_collection.aggregate(
            [
                {
                    "$geoNear": {
                        "near": {"type": "Point", "coordinates": [long, lat]},
                        "spherical": False,
                        "distanceField": "calcDistance",
                        "query": { "type": type },
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
            dist = (house['calcDistance'] if house['calcDistance'] > coeff else coeff)
            score += population * coeff / dist
        max_score = (await self.points_collection.find({"type": "special"}).sort("score", -1).limit(1).to_list(length=None))[0]["score"]
        is_mfc = (20 if (await self.points_collection.find({"type": "special", "location.coordinates" : [long, lat]}).to_list(length=None)) else 0)
        is_mfc_near = (-10 * len(await self.find_close_points(lat, long, distance, 'special')) if is_mfc > 0 else 0)
        score = (100 if (score * 100 / max_score) + is_mfc > 100 else (score * 100 / max_score) + is_mfc)
        score = (score if score + is_mfc_near < 0 else score + is_mfc_near)
        response["point"] = {"score": score, "coords": [lat, long]}
        return response

    async def add_points(self, point: list[PointInfo]) -> None:
        await self.points_collection.insert_many([p.dict() for p in point])

    async def add_postamatus(self, postamat_lat: float, postamat_long: float, username: str, score: float) -> None:
        if (await self.postamatus_collection.find({"location.coordinates": [postamat_long, postamat_lat]}).to_list(length=None)):
            raise PostamatExist()
        await self.postamatus_collection.insert_one({"location" : {"coordinates" : [postamat_long, postamat_lat]}, "username" : username, "score" : score})
        return None

    async def del_postamatus(self, postamat_lat: float, postamat_long: float, username: str) -> None:
        if postamat := (await self.postamatus_collection.find({"location.coordinates": [postamat_long, postamat_lat]}).to_list(length=None)):
            if (postamat[0]["username"] == username):
                await self.postamatus_collection.delete_one({"location" : {"coordinates" : [postamat_long, postamat_lat]}, "username" : username})
            else:
                raise NotUsersPostamat()
        else:
            raise PostamatNotExist()
        return None

    async def get_postamats(self, username: str) -> list[dict] | None:
        if postamats := (await self.postamatus_collection.find({"username" : username}, {"_id": 0}).to_list(length=None)):
            return postamats
        else:
            raise PostamatsNotFound()

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
