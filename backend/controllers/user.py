# backend/controllers/user.py

from fastapi import HTTPException
from datetime import datetime
from passlib.context import CryptContext
import logging

from async_eav import eav
from models import CreateUserRequest, UpdateUserRequest, DeleteUserRequest

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def delete_user(data: DeleteUserRequest):
    user_id = f"user:{data.username}"
    await eav.delete_entity(user_id)
    return {"message": f"Пользователь {data.username} удалён"}

async def update_user(data: UpdateUserRequest):
    user_id = f"user:{data.username}"
    user_data = await eav.get_all_attributes(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if data.password:
        hashed_password = pwd_context.hash(data.password)
        await eav.set_attribute(user_id, "password", hashed_password)

    if data.role:
        await eav.set_attribute(user_id, "role", data.role)

    return {"message": "Пользователь обновлён"}


# async def get_user(username: str, current_user: dict = Depends(get_current_user)):
async def get_user(username: str):
    user_id = f"user:{username}"
    user_data = await eav.get_all_attributes(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {
        "username": username,
        "role": user_data.get("role", "user"),
        "created_at": user_data.get("created_at")
    }


# async def create_user(data: CreateUserRequest, current_user: dict = Depends(get_current_user)):
async def create_user(data: CreateUserRequest):
    # Проверим, что такого пользователя ещё нет
    existing = await eav.client.exists(f"user:{data.username}")
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    # Хешируем пароль
    hashed_password = pwd_context.hash(data.password)
    await eav.create_entity(
        f"user:{data.username}",
        attributes={
            "username": data.username,
            "password": hashed_password,
            "role": data.role,
            "created_at": datetime.utcnow().isoformat()
        }
    )
    return {"message": f"Пользователь {data.username} создан"}
