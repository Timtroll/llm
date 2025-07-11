from fastapi import FastAPI
import subprocess
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Конфигурация доступных моделей
MODELS_CONFIG = {
    "llama-7b": {
        "path": "/llama.cpp/models/llama-7b.Q4_0.gguf",
        "default_tokens": 128,
        "default_temp": 0.7
    },
    "model-q4": {
        "path": "/llama.cpp/models/model-q4_K.gguf",
        "default_tokens": 128,
        "default_temp": 0.7
    }
}

# 📌 История сообщений (в памяти)
HISTORY = {}

@app.post("/generate")
async def generate_text(prompt: dict):
    # Проверка наличия обязательных полей
    if "text" not in prompt:
        logger.error("Поле 'text' отсутствует в запросе")
        return {"error": "Поле 'text' обязательно в запросе"}

    # Определение сессии
    session_id = prompt.get("session_id", "default")

    # Обработка сброса истории
    if prompt.get("reset", False):
        HISTORY.pop(session_id, None)

    # Получение имени модели (по умолчанию первая из доступных)
    model_name = prompt.get("model", list(MODELS_CONFIG.keys())[0])
    if model_name not in MODELS_CONFIG:
        logger.error(f"Модель '{model_name}' не найдена в конфигурации")
        return {"error": f"Модель '{model_name}' не поддерживается"}

    model_config = MODELS_CONFIG[model_name]

    # Получение базовых параметров генерации
    n_tokens = prompt.get("n_tokens", model_config["default_tokens"])
    temperature = prompt.get("temp", model_config["default_temp"])

    # Получение дополнительных параметров
    top_p = prompt.get("top_p")
    top_k = prompt.get("top_k")
    repeat_penalty = prompt.get("repeat_penalty")
    seed = prompt.get("seed")

    # Проверка наличия исполняемого файла
    main_path_candidates = [
        "/llama.cpp/build/bin/llama-cli",
        "/llama.cpp/build/llama-cli",
        "/llama.cpp/build/bin/main",
        "/llama.cpp/build/main"
    ]

    main_path = None
    for path in main_path_candidates:
        if os.path.isfile(path):
            main_path = path
            break

    if not main_path:
        logger.error("Исполняемый файл не найден")
        return {"error": "Исполняемый файл (llama-cli или main) не найден"}

    # Формирование промпта с историей
    russian_instruction = (
        "Ты — русскоязычный помощник. Всегда отвечай только на русском языке, грамотно и понятно.\n\n"
    )

    # Восстановим историю, если есть
    history_messages = HISTORY.get(session_id, [])
    current_user_input = prompt["text"]
    history_messages.append(f"Пользователь: {current_user_input}")

    full_prompt = russian_instruction + "\n".join(history_messages)

    # Формирование команды
    command = [
        main_path,
        "-m", model_config["path"],
        "-p", full_prompt,
        "-n", str(n_tokens),
        "--temp", str(temperature)
    ]

    # Добавляем дополнительные аргументы если они заданы
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

        response = process.stdout.strip()
        logger.info("Генерация текста успешна")

        # Добавим ответ в историю
        history_messages.append(f"Помощник: {response}")
        HISTORY[session_id] = history_messages

        return {
            "response": response,
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


# 📌 Примеры вызова:
"""
1) Новый диалог, сброс истории:
POST /generate
Content-Type: application/json

{
    "text": "Привет! Как дела?",
    "reset": true,
    "session_id": "user123"
}

2) Продолжение диалога с предыдущей сессией:
POST /generate
Content-Type: application/json

{
    "text": "А можешь объяснить подробнее?",
    "session_id": "user123"
}

3) Смена модели и параметры генерации:
POST /generate
Content-Type: application/json

{
    "text": "Напиши рассказ про робота",
    "model": "model-q4",
    "temp": 0.8,
    "n_tokens": 150,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "seed": 42,
    "session_id": "user456"
}

4) Минимальный запрос (используются дефолты и одна сессия):
POST /generate
Content-Type: application/json

{
    "text": "Расскажи анекдот"
}
"""
