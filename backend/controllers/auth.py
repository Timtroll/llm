# backend/controllers/auth.py

from fastapi import HTTPException
from datetime import datetime, timedelta

from async_eav import eav
from security import pwd_context, create_access_token
from models import LoginRequest

from settings import settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

async def login_user(request: LoginRequest) -> dict:
    user_id = f"user:{request.username}"
    user_data = await eav.get_all_attributes(user_id)

    if not user_data or not pwd_context.verify(request.password, user_data.get("password")):
        raise HTTPException(status_code=401, detail="Неверные данные")
    
    role = user_data.get("role", "")
    if not role:
        raise HTTPException(status_code=401, detail="Нет роли")

    token = create_access_token({"sub": request.username, "role": role})
    await eav.set_attribute(f"token:{token}", "user", request.username)
    await eav.set_attribute(
        f"token:{token}",
        "expires",
        (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()
    )
    
    return {
        "token": token,
        "user": {"username": request.username, "role": role}
    }
