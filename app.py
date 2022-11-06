from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from database.models import UserDataReg
from database.mongo import Mongo
from database.exceptions import SamePassword, UserNotFound, PostamatExist, PostamatsNotFound, PostamatNotExist, NotUsersPostamat

# from utils.dataset_worker import DatasetRow, get_data
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PATCH", "DELETE", "PUT"],
    allow_headers=["*"],
)


class AuthData(BaseModel):
    login: str
    password: str


class Token(BaseModel):
    token: str


@app.post("/login", response_model=Token)
async def get_token(data: AuthData):
    """
    Авторизация пользователя путем отправки логина и пароля.
    В ответ вы получаете токен
    """
    if await Mongo.find_user(username=data.login, password=data.password):
        return Token(token=data.login + "_" + data.password)
    raise HTTPException(status_code=403, detail="Неправильный логин или пароль")


class UserOut(BaseModel):
    username: str
    full_name: str = "fake name"
    birthday: datetime = datetime.utcnow()


@app.get("/me", response_model=UserOut)
async def get_my_data(token: str = Header()):
    """Получение данных о пользователе по токену"""
    username, password = token.split("_")
    if user := await Mongo.find_user(username=username, password=password):
        del user[0]["password"]
        return UserOut(**user[0])
    raise HTTPException(status_code=403, detail="Ошибка при валидации токена")


@app.post("/password", response_model=UserOut)
async def change_user_password(new_password: str, token: str = Header()):
    """Получение данных о пользователе по токену"""
    username, password = token.split("_")
    try:
        await Mongo.edit_password(username=username, password=password, new_password=new_password)
    except SamePassword:
        raise HTTPException(status_code=400, detail='Новый пароль не может совпадать со старым')
    except UserNotFound:
        raise HTTPException(status_code=403, detail='Пользователь не авторизован')
    except Exception:
        raise HTTPException(status_code=500, detail='Неожиданная ошибка')
    raise HTTPException(status_code=200, detail='Пароль успешно изменен')


class GenericResponse(BaseModel):
    detail: str


@app.post("/reg", response_model=GenericResponse)
async def register_new_user(user_data: UserDataReg):
    try:
        await Mongo.register_user(user_data=user_data)
    except ValueError:
        raise HTTPException(status_code=403, detail="Пользователь уже есть в базе!")
    return GenericResponse(detail="Пользователь успешно создан!")


@app.get("/users")
async def get_all_users() -> list[UserOut]:
    return [UserOut(**u) for u in await Mongo.get_all_users()]


@app.get("/points/near")
async def get_points_near_given(lat: float, long: float, type: str = 'house') -> list[dict]:
    return await Mongo.find_close_points(lat=lat, long=long, type=type)


@app.get("/points/score")
async def get_points_near_given(lat: float, long: float) -> list[dict]:
    return await Mongo.calculate_point_score(lat=lat, long=long)

@app.post("/points/postamat", response_model=UserOut)
async def add_new_postamat(lat: float, long: float, score: float, token: str = Header()):
    username = token.split("_")[0]
    try:
        await Mongo.add_postamatus(postamat_lat=lat, postamat_long=long, username=username, score=score)
    except PostamatExist:
        raise HTTPException(status_code=403, detail="Постамат уже существует!")
    raise HTTPException(status_code=200, detail='Постамат успешно поставлен')
    
@app.delete("/points/postamat", response_model=UserOut)
async def delete_postamat(lat: float, long: float, token: str = Header()):
    username = token.split("_")[0]
    try:
        await Mongo.del_postamatus(postamat_lat=lat, postamat_long=long, username=username)
    except PostamatNotExist:
        raise HTTPException(status_code=403, detail="Постамат не существует!")
    except NotUsersPostamat:
        raise HTTPException(status_code=400, detail="Пользователь не может удалить данный постамат")
    raise HTTPException(status_code=200, detail='Постамат успешно удален')

@app.get("/points/my")
async def get_my_postamats(token: str = Header()) -> list[dict] | None:
    username = token.split("_")[0]
    try:
        return await Mongo.get_postamats(username=username)
    except PostamatsNotFound:
        raise HTTPException(status_code=403, detail="Постаматы не найдены")