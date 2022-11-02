from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from database.models import UserDataReg
from database.mongo import Mongo

from utils.dataset_worker import DatasetRow, get_data
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


@app.get('/addresses', response_model=list[DatasetRow])
async def get_list_of_addresses() -> list[DatasetRow]:
    """Получение списка адресов с количеством жителей"""
    return get_data()


class AuthData(BaseModel):
    login: str
    password: str


class Token(BaseModel):
    token: str


users = {
    'timofeev': 'nikolas',
    'rawman': 'cave'
}


@app.post('/login', response_model=Token)
async def get_token(data: AuthData):
    """
    Авторизация пользователя путем отправки логина и пароля.
    В ответ вы получаете токен
    """
    if await Mongo.find_user(username=data.login, password=data.password):
        return Token(token=data.login + "_" + data.password)
    raise HTTPException(status_code=403, detail='Неправильный логин или пароль')


class UserOut(BaseModel):
    username: str
    full_name: str = 'fake name'    
    birthday: datetime = datetime.utcnow()


@app.get('/me', response_model=UserOut)
async def get_my_data(token: str = Header()):
    """Получение данных о пользователе по токену"""
    username, password = token.split('_')
    if user := await Mongo.find_user(username=username, password=password):
        del user['password']
        return UserOut(**user)
    raise HTTPException(status_code=403, detail='Ошибка при валидации токена')


class GenericResponse(BaseModel):
    detail: str


@app.post('/reg', response_model=GenericResponse)
async def register_new_user(user_data: UserDataReg):
    try:
        await Mongo.register_user(user_data=user_data)
    except ValueError:
        raise HTTPException(status_code=403, detail='Пользователь уже есть в базе!')
    return GenericResponse(detail='Пользователь успешно создан!')

@app.get('/users')
async def get_all_users() -> list[UserOut]:
    return [UserOut(**u) for u in await Mongo.get_all_users()]
