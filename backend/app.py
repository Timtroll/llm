# backend/app.py

import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any
from passlib.context import CryptContext
from security import get_current_user

from controllers.auth import login_user
from controllers.users import list_users
from controllers.user import get_user, create_user, update_user, delete_user
from controllers.models import list_models
from controllers.generate import generate_text
from models import CreateUserRequest, LoginRequest, RegisterRequest, UpdateUserRequest, DeleteUserRequest
from utils import health

# Поиск в интернет, можно выключить при необходимости
SEARCH_ENABLED = True

# Инициализация хеширования паролей
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Middleware для обработки X-Forwarded-Proto
class TrustProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}, scheme={request.scope['scheme']}")
        if request.headers.get("X-Forwarded-Proto") == "https":
            request.scope["scheme"] = "https"
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

app.add_middleware(TrustProxyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Маршруты
@app.get("/api/health")
def health_check():
    return health()

########################### START роуты для работы с пользователями


@app.get("/api/users")
async def users(
    field: str,
    value: str,
    request: Request,
    # current_user: dict = Depends(get_current_user)
):
    return await list_users(field, value, request)


@app.get("/api/user")
async def user(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    return await get_user(username)


@app.post("/api/user/create")
async def user_create(
    data: CreateUserRequest,
    # current_user: dict = Depends(get_current_user)
):
    return await create_user(data)


@app.post("/api/user/update")
async def user_update(
    data: UpdateUserRequest,
    # current_user: dict = Depends(get_current_user)
):
    return await update_user(data)


@app.post("/api/user/delete")
async def user_delete(
    data: DeleteUserRequest,
    # current_user: dict = Depends(get_current_user)
):
    return await delete_user(data)


########################### END роуты для работы с пользователями


@app.post("/api/user/login")
async def login(request: LoginRequest):
    return await login_user(request)


# список моделей, синхронизированных с EAV
@app.get("/api/models")
async def models_list():
    return await list_models()

@app.post("/api/generate")
async def test_generate(
    prompt: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    return await generate_text(prompt, current_user)
