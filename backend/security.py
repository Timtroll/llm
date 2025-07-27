# backend/security.py

import jwt
import logging

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta

from async_eav import eav
from settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# OAuth2 схема для извлечения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/user/login")

# Настройка хеширования паролей (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Генерация JWT
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "your-app-name",
        "role": data.get("role", "user"),
        # "custom_field": "value"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Валидация JWT
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Недействительный токен!")
        # Проверка существования пользователя в EAV
        user_data = await eav.get_all_attributes(f"user:{username}")
        if not user_data:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return {"username": username, "role": user_data.get("role", "user")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")

