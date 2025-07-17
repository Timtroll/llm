from unittest.util import strclass
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # Добавляем импорт Pydantic
import subprocess
import logging
import os
import glob
from datetime import datetime
from typing import Dict, List, Any
import json
import re
import httpx


SEARCH_ENABLED = True  # можно выключить при необходимости

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем модель для валидации JSON-запроса
class LoginRequest(BaseModel):
    username: str
    password: str

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

HISTORY = {}


async def search_internet(query: str) -> str:
    """
    Выполняет поиск в интернете (используя DuckDuckGo API или аналогичный сервис)
    и возвращает краткий результат.
    """
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

@app.get("/api/health")
def health():
    return {"status": "ok"}


# @app.post("/login")
# async def login(username: str = Form(...), password: str = Form(...)):
#     if username == "admin" and password == "secret":
#         token = "c8f3e0e7f2c49aa647d944fa19b7a81e5fbd49e6c534a3a8c22ef13ccf7bd189"
#         return JSONResponse({"token": token})
#     raise HTTPException(status_code=401, detail="Неверные данные")

@app.post("/api/login")
async def login(request: LoginRequest):
    if request.username == "admin" and request.password == "secret":
        return {
            "token": "c8f3e0e7f2c49aa647d944fa19b7a81e5fbd49e6c534a3a8c22ef13ccf7bd189",
            "user": {"username": request.username}
        }
    raise HTTPException(status_code=401, detail="Неверные данные")


@app.get("/api/models")
async def list_models():
    model_dir = "/llama.cpp/models/"
    try:
        # Поиск всех файлов *.gguf в директории
        model_files = glob.glob(os.path.join(model_dir, "*.gguf"))
        # models = []
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
            # Извлечение имени файла без пути и расширения
            model_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Получение размера файла
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Размер в МБ
            
            # Получение даты модификации
            mod_time = os.path.getmtime(file_path)
            mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Попытка получить дополнительную информацию о модели
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
                    # Попытка получить версию и дополнительные метаданные
                    command = [main_path, "-m", file_path, "--verbose"]
                    process = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    if process.returncode == 0:
                        output = process.stdout.strip()
                        # Пытаемся извлечь версию, параметры и архитектуру
                        for line in output.splitlines():
                            if "version" in line.lower():
                                model_info["version"] = line.split(":")[-1].strip()
                            if "parameters" in line.lower():
                                model_info["parameters"] = line.split(":")[-1].strip()
                            if "architecture" in line.lower():
                                model_info["architecture"] = line.split(":")[-1].strip()
                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    logger.warning(f"Не удалось получить метаданные для {model_name}: {str(e)}")

            # models.append(model_info)

        # return {"models": models}
        return models
    except Exception as e:
        logger.error(f"Ошибка при поиске моделей: {str(e)}")
        return {"error": f"Ошибка при поиске моделей: {str(e)}"}


@app.post("/api/generate")
async def generate_text(prompt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует текст с использованием LLM и возвращает форматированный ответ в формате JSON.
    
    Args:
        prompt: Словарь с параметрами запроса, включая 'text', 'session_id', 'model' и др.
    
    Returns:
        Словарь с историей, ответом модели и параметрами или с ошибкой.
    """
    if "text" not in prompt:
        logger.error("Поле 'text' отсутствует в запросе")
        return {"error": "Поле 'text' обязательно в запросе"}

    session_id = prompt.get("session_id", "default")
    if prompt.get("reset", False):
        HISTORY.pop(session_id, None)

    text = prompt["text"]
    use_search = prompt.get("use_search", False)

    internet_info = ""
    if use_search:
        logger.info(f"Активирован поиск в интернете для: {text}")
        internet_info = await search_internet(text)

    # Вставим найденную информацию в промпт
    if internet_info:
        text += f"\n\nСправочная информация из интернета: {internet_info}"

    # Передаем дальше в твой текущий пайплайн генерации (оставим как есть)
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

    # Поиск исполняемого файла
    main_path_candidates = [
        "/llama.cpp/build/bin/llama-cli",
        "/llama.cpp/build/llama-cli",
        "/llama.cpp/build/bin/main",
        "/llama.cpp/build/main"
    ]
    main_path = next((p for p in main_path_candidates if os.path.isfile(p)), None)
    if not main_path:
        logger.error("Исполняемый файл не найден")
        return {"error": "Исполняемый файл (llama-cli или main) не найден"}

    # Формирование истории
    history_messages: List[Dict[str, str]] = HISTORY.get(session_id, [])
    current_user_input = prompt["text"] + "\n"
    history_messages.append({"role": "user", "content": current_user_input})


    # Формирование промпта для модели
    russian_instruction = (
        "Ты — русскоязычный помощник. Всегда отвечай только на русском языке, грамотно и понятно. Ответы давай в формате Markdown.\n"
        # "Отвечай строго в формате JSON: {\"assistant\": \"текст ответа\"}\n\n"
    )

    # Добавляем инструкцию только если история пуста (начало беседы)
    full_prompt = russian_instruction if not history_messages else ""
    for msg in history_messages:
        if msg["role"] == "user":
            full_prompt += f"user: {msg['content']}\n"
        # elif msg["role"] == "assistant":
        #     full_prompt += f"assistant: {msg['content']}\n"

    # Формирование команды для запуска модели
    command = [
        main_path,
        "-m", model_config["path"],
        "-p", full_prompt,
        "-n", str(n_tokens),
        "--temp", str(temperature),
        "-cnv",  # Включаем режим диалога
        # "-chat-template", "chatml"  # Используем шаблон ChatML для структурированного диалога
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

        # Извлечение ответа ассистента
        clean_response = extract_assistant_response(raw_response)
        logger.info(f"Чистый ответ модели:\n{clean_response}")

        # Добавление ответа в историю
        history_messages.append({"role": "assistant", "content": clean_response})
        HISTORY[session_id] = history_messages


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

def extract_assistant_response(raw_response: str) -> strclass:
    """
    Извлекает ответ ассистента из raw_response.
    Ищет текст между "assistant" и "> EOF by user",
    удаляя лидирующие и конечные пробелы и переводы строк.
    """
    result = ""

    # Найти блок между "assistant" и "> EOF by user"
    match = re.search(r"assistant\s*(.*?)\s*> EOF by user", raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        result = match.group(1).strip()

    return result

