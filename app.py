from fastapi import FastAPI
import subprocess
import json
import logging
import os
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

#         # "-m", "/llama.cpp/models/llama-7b.Q4_0.gguf",
#         "-m", "/llama.cpp/models/model-q4_K.gguf",

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

@app.post("/generate")
async def generate_text(prompt: dict):
    # Проверка наличия обязательных полей
    if "text" not in prompt:
        logger.error("Поле 'text' отсутствует в запросе")
        return {"error": "Поле 'text' обязательно в запросе"}
    
    # Получение имени модели (по умолчанию первая из доступных)
    model_name = prompt.get("model", list(MODELS_CONFIG.keys())[0])
    if model_name not in MODELS_CONFIG:
        logger.error(f"Модель '{model_name}' не найдена в конфигурации")
        return {"error": f"Модель '{model_name}' не поддерживается"}
    
    model_config = MODELS_CONFIG[model_name]
    
    # Получение параметров генерации из запроса или использование значений по умолчанию
    n_tokens = prompt.get("n_tokens", model_config["default_tokens"])
    temperature = prompt.get("temp", model_config["default_temp"])
    
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
    
    russian_instruction = (
        "Ты — русскоязычный помощник. Всегда отвечай только на русском языке, грамотно и понятно.\n\n"
    )
    final_prompt = russian_instruction + prompt["text"]

    # Запуск llama.cpp для генерации текста
    command = [
        main_path,
        "-m", model_config["path"],
        "-p", final_prompt,
        "-n", str(n_tokens),
        "--temp", str(temperature)
    ]
    
    try:
        logger.info(f"Выполнение команды: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=300)
        
        if process.returncode != 0:
            logger.error(f"Ошибка выполнения команды: {process.stderr}")
            return {"error": f"Ошибка выполнения команды: {process.stderr}"}
        
        response = process.stdout
        logger.info("Генерация текста успешна")
        return {
            "response": response,
            "model": model_name,
            "parameters": {
                "n_tokens": n_tokens,
                "temperature": temperature
            }
        }
    except subprocess.TimeoutExpired:
        logger.error("Превышено время ожидания генерации")
        return {"error": "Превышено время ожидания генерации"}
    except Exception as e:
        logger.error(f"Ошибка при генерации: {str(e)}")
        return {"error": f"Ошибка при генерации: {str(e)}"}

# from fastapi import FastAPI
# import subprocess
# import json
# import logging
# import os

# # Настройка логирования
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI()

# @app.post("/generate")
# async def generate_text(prompt: dict):
#     # Проверка наличия ключа 'text' в запросе
#     if "text" not in prompt:
#         logger.error("Поле 'text' отсутствует в запросе")
#         return {"error": "Поле 'text' обязательно в запросе"}
    
#     # Проверка наличия исполняемого файла
#     main_path_candidates = ["/llama.cpp/build/bin/llama-cli", "/llama.cpp/build/llama-cli", "/llama.cpp/build/bin/main", "/llama.cpp/build/main"]
#     main_path = None
#     for path in main_path_candidates:
#         if os.path.isfile(path):
#             main_path = path
#             break
#     if not main_path:
#         logger.error("Исполняемый файл (llama-cli или main) не найден ни в /llama.cpp/build/, ни в /llama.cpp/build/bin/")
#         return {"error": "Исполняемый файл (llama-cli или main) не найден ни в /llama.cpp/build/, ни в /llama.cpp/build/bin/"}
    
#     # Запуск llama.cpp для генерации текста
#     command = [
#         main_path,
#         # "-m", "/llama.cpp/models/llama-7b.Q4_0.gguf",
#         "-m", "/llama.cpp/models/model-q4_K.gguf",
#         "-p", prompt["text"],
#         "-n", "128",  # Количество токенов для генерации
#         "--temp", "0.7"
#     ]
#     try:
#         logger.info(f"Выполнение команды: {' '.join(command)}")
#         process = subprocess.run(command, capture_output=True, text=True, timeout=300)
#         if process.returncode != 0:
#             logger.error(f"Ошибка выполнения команды: {process.stderr}")
#             return {"error": f"Ошибка выполнения команды: {process.stderr}"}
#         response = process.stdout
#         logger.info("Генерация текста успешна")
#         return {"response": response}
#     except subprocess.TimeoutExpired:
#         logger.error("Превышено время ожидания генерации")
#         return {"error": "Превышено время ожидания генерации"}
#     except Exception as e:
#         logger.error(f"Ошибка при генерации: {str(e)}")
#         return {"error": f"Ошибка при генерации: {str(e)}"}
