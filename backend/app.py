import jwt
import subprocess
import logging
import os
import glob
import json
import re
import httpx
# import base64

from fastapi import FastAPI, Request, HTTPException, Depends
# from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from typing import Dict, Any
# import asyncio
# import redis.asyncio as redis
from passlib.context import CryptContext

from models import CreateUserRequest, LoginRequest, RegisterRequest, UpdateUserRequest, DeleteUserRequest
from utils import health

# Секретный ключ для подписи JWT
SECRET_KEY = "c8f3e0e7f2c49aa647d944fa19b7a81e5fbd49e6c534a3a8c22ef13ccf7bd189"  # Замените на безопасный ключ
# SECRET_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Поиск в интернет, можно выключить при необходимости
SEARCH_ENABLED = True

# Конфигурация моделей
MODELS_CONFIG = {
    "llama-7b": {
        "path": "/llama.cpp/models/llama-7b.Q4_0.gguf",
        "default_tokens": 2048,
        "default_temp": 0.7
    },
    "model-q4": {
        "path": "/llama.cpp/models/model-q4_K.gguf",
        "default_tokens": 2048,
        "default_temp": 0.7
    }
}

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

# OAuth2 схема для извлечения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/user/login")


# Генерация JWT
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "your-app-name",
        "role": data.get("role", "user"),
        "custom_field": "value"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Валидация JWT
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Недействительный токен")
        # Проверка существования пользователя в EAV
        user_data = await eav.get_all_attributes(f"user:{username}")
        if not user_data:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return {"username": username, "role": user_data.get("role", "user")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")


async def search_internet(query: str) -> str:
    if not SEARCH_ENABLED:
        return "Поиск в интернете отключен."
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
            )
            data = resp.json()
            abstract = data.get("Abstract")
            if abstract:
                return abstract
            related = data.get("RelatedTopics", [])
            if related:
                return related[0].get("Text", "Не найдено подробностей.")
            return "По запросу ничего не найдено."
    except Exception as e:
        logger.error(f"Ошибка поиска в интернете: {e}")
        return "Ошибка при попытке поиска в интернете."


# Маршруты
@app.get("/api/health")
def health_check():
    return health()

########################### START роуты для работы с пользователями
# @app.post("/api/register")
# async def register(request: RegisterRequest):
#     user_id = f"user:{request.username}"
#     existing_user = await eav.get_all_attributes(user_id)
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
#     hashed_password = pwd_context.hash(request.password)
#     await eav.set_attribute(user_id, "password", hashed_password)
#     await eav.set_attribute(user_id, "roles", json.dumps(request.roles))
#     await eav.set_attribute(user_id, "created_at", datetime.utcnow().isoformat())
    
#     token = create_access_token({"sub": request.username, "roles": request.roles})
#     await eav.set_attribute(f"token:{token}", "user", request.username)
#     await eav.set_attribute(f"token:{token}", "expires", (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat())
    
#     return {
#         "token": token,
#         "user": {"username": request.username, "roles": request.roles}
#     }



from controllers.users import list_users
from controllers.user import get_user, create_user, update_user, delete_user

@app.get("/api/users")
async def users(field: str, value: str, request: Request):
    return await list_users(field, value, request)


@app.get("/api/user")
async def user(username: str):
    return await get_user(username)


@app.post("/api/user/create")
async def user_create(data: CreateUserRequest):
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
    user_id = f"user:{request.username}"
    user_data = await eav.get_all_attributes(user_id)
    print('user_data')
    print(user_data)
    if not user_data or not pwd_context.verify(request.password, user_data.get("password")):
        raise HTTPException(status_code=401, detail="Неверные данные")
    
    role = user_data.get("role", "")
    if not role:
        raise HTTPException(status_code=401, detail="Нет роли")

    token = create_access_token({"sub": request.username, "role": role})
    await eav.set_attribute(f"token:{token}", "user", request.username)
    await eav.set_attribute(f"token:{token}", "expires", (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat())
    
    return {
        "token": token,
        "user": {"username": request.username, "role": role}
    }


# @app.get("/api/protected")
# async def protected_route(current_user: dict = Depends(get_current_user)):
#     return {"message": f"Привет, {current_user['username']}!"}


@app.get("/api/models")
async def list_models():
    model_dir = "/llama.cpp/models/"
    try:
        model_files = glob.glob(os.path.join(model_dir, "*.gguf"))
        models = {}
        main_path = next(
            (p for p in [
                "/llama.cpp/build/bin/llama-cli",
                "/llama.cpp/build/llama-cli",
                "/llama.cpp/build/bin/main",
                "/llama.cpp/build/main"
            ] if os.path.isfile(p)), None
        )

        for file_path in model_files:
            model_name = os.path.splitext(os.path.basename(file_path))[0]
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            mod_time = os.path.getmtime(file_path)
            mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            
            models[model_name] = {
                "name": model_name,
                "path": file_path,
                "size": round(file_size, 2),
                "modified": mod_date,
                "version": "unknown",
                "parameters": "unknown",
                "architecture": "unknown",
                "default_tokens": 128,
                "default_temp": 0.7
            }

            if main_path:
                try:
                    command = [main_path, "-m", file_path, "--verbose"]
                    process = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    if process.returncode == 0:
                        output = process.stdout.strip()
                        for line in output.splitlines():
                            if "version" in line.lower():
                                models[model_name]["version"] = line.split(":")[-1].strip()
                            if "parameters" in line.lower():
                                models[model_name]["parameters"] = line.split(":")[-1].strip()
                            if "architecture" in line.lower():
                                models[model_name]["architecture"] = line.split(":")[-1].strip()
                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    logger.warning(f"Не удалось получить метаданные для {model_name}: {str(e)}")

        return models
    except Exception as e:
        logger.error(f"Ошибка при поиске моделей: {str(e)}")
        return {"error": f"Ошибка при поиске моделей: {str(e)}"}


@app.post("/api/generate")
async def generate_text(prompt: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    if "text" not in prompt:
        logger.error("Поле 'text' отсутствует в запросе")
        return {"error": "Поле 'text' обязательно в запросе"}

    session_id = prompt.get("session_id", f"user:{current_user['username']}")
    if prompt.get("reset", False):
        await eav.delete_entity(f"history:{session_id}")

    text = prompt["text"]
    use_search = prompt.get("use_search", False)

    internet_info = ""
    if use_search:
        logger.info(f"Активирован поиск в интернете для: {text}")
        internet_info = await search_internet(text)

    if internet_info:
        text += f"\n\nСправочная информация из интернета: {internet_info}"
    prompt["text"] = text

    model_name = prompt.get("model", list(MODELS_CONFIG.keys())[0])
    if model_name not in MODELS_CONFIG:
        logger.error(f"Модель '{model_name}' не найдена в конфигурации")
        return {"error": f"Модель '{model_name}' не поддерживается"}

    model_config = MODELS_CONFIG[model_name]
    n_tokens = prompt.get("n_tokens", model_config["default_tokens"])
    temperature = prompt.get("temp", model_config["default_temp"])
    top_p = prompt.get("top_p")
    top_k = prompt.get("top_k")
    repeat_penalty = prompt.get("repeat_penalty")
    seed = prompt.get("seed")

    main_path = next(
        (p for p in [
            "/llama.cpp/build/bin/llama-cli",
            "/llama.cpp/build/llama-cli",
            "/llama.cpp/build/bin/main",
            "/llama.cpp/build/main"
        ] if os.path.isfile(p)), None
    )
    if not main_path:
        logger.error("Исполняемый файл не найден")
        return {"error": "Исполняемый файл (llama-cli или main) не найден"}

    # Получение истории из EAV
    history_data = await eav.get_all_attributes(f"history:{session_id}")
    history_messages = []
    for key, value in history_data.items():
        if key.startswith("message:"):
            history_messages.append(json.loads(value))
    history_messages.sort(key=lambda x: x.get("timestamp", 0))

    current_user_input = {"role": "user", "content": text + "\n", "timestamp": datetime.utcnow().isoformat()}
    history_messages.append(current_user_input)
    await eav.set_attribute(f"history:{session_id}", f"message:{len(history_messages)}", json.dumps(current_user_input))

    russian_instruction = (
        "Ты — русскоязычный помощник. Всегда отвечай только на русском языке, грамотно и понятно. Ответы давай в формате Markdown.\n"
    )

    full_prompt = russian_instruction if not history_messages else ""
    for msg in history_messages:
        if msg["role"] == "user":
            full_prompt += f"user: {msg['content']}\n"

    command = [
        main_path,
        "-m", model_config["path"],
        "-p", full_prompt,
        "-n", str(n_tokens),
        "--temp", str(temperature),
        "-cnv",
    ]

    if top_p is not None:
        command.extend(["--top-p", str(top_p)])
    if top_k is not None:
        command.extend(["--top-k", str(top_k)])
    if repeat_penalty is not None:
        command.extend(["--repeat-penalty", str(repeat_penalty)])
    if seed is not None:
        command.extend(["--seed", str(seed)])

    try:
        logger.info(f"Выполнение команды: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True, timeout=300)

        if process.returncode != 0:
            logger.error(f"Ошибка выполнения команды: {process.stderr}")
            return {"error": f"Ошибка выполнения команды: {process.stderr}"}

        raw_response = process.stdout
        logger.info(f"Сырой ответ модели:\n={raw_response}=")

        clean_response = extract_assistant_response(raw_response)
        logger.info(f"Чистый ответ модели:\n{clean_response}")

        # Сохранение ответа в EAV
        assistant_response = {"role": "assistant", "content": clean_response, "timestamp": datetime.utcnow().isoformat()}
        history_messages.append(assistant_response)
        await eav.set_attribute(f"history:{session_id}", f"message:{len(history_messages)}", json.dumps(assistant_response))

        return {
            "history": history_messages,
            "response": clean_response,
            "model": model_name,
            "session_id": session_id,
            "parameters": {
                "n_tokens": n_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty,
                "seed": seed
            }
        }

    except subprocess.TimeoutExpired:
        logger.error("Превышено время ожидания генерации")
        return {"error": "Превышено время ожидания генерации"}
    except Exception as e:
        logger.error(f"Ошибка при генерации: {str(e)}")
        return {"error": f"Ошибка при генерации: {str(e)}"}


def extract_assistant_response(raw_response: str) -> str:
    result = ""
    match = re.search(r"assistant\s*(.*?)\s*> EOF by user", raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        result = match.group(1).strip()
    return result
