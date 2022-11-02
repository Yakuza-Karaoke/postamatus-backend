from pydantic import BaseModel


class UserData(BaseModel):
    username: str
    full_name: str


class UserDataReg(UserData):
    password: str


class Point(BaseModel):
    lat: float
    long: float


class PointInfo(Point):
    address: str
    population: int
