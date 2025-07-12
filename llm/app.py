from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import logging
import os

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


def extract_last_assistant_response(full_prompt: str, raw_output: str) -> str:
    """
    Из ответа модели убираем всё, что уже было отправлено как prompt,
    и возвращает только последний абзац (разделитель — \n\n).
    """
    if raw_output.startswith(full_prompt):
        response = raw_output[len(full_prompt):].strip()
    else:
        response = raw_output.strip()
    response = response.replace("> EOF by user", "").strip()

    # Разбиваем на абзацы
    paragraphs = [p.strip() for p in response.split("\n\n") if p.strip()]
    if paragraphs:
        return paragraphs[-1]
    else:
        return response 


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate_text(prompt: dict):
    if "text" not in prompt:
        logger.error("Поле 'text' отсутствует в запросе")
        return {"error": "Поле 'text' обязательно в запросе"}

    session_id = prompt.get("session_id", "default")

    if prompt.get("reset", False):
        HISTORY.pop(session_id, None)

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

    # Собираем историю
    history_messages = HISTORY.get(session_id, [])
    current_user_input = prompt["text"]
    history_messages.append({"role": "user", "content": current_user_input})

    # Промпт для модели
    russian_instruction = (
        "Ты — русскоязычный помощник. Всегда отвечай только на русском языке, грамотно и понятно.\n\n"
    )
    full_prompt = russian_instruction
    for msg in history_messages:
        if msg["role"] == "user":
            full_prompt += f"Пользователь: {msg['content']}\n"
        elif msg["role"] == "assistant":
            full_prompt += f"Помощник: {msg['content']}\n"

    command = [
        main_path,
        "-m", model_config["path"],
        "-p", full_prompt,
        "-n", str(n_tokens),
        "--temp", str(temperature)
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

        raw_response = process.stdout.strip()
        logger.debug(f"Сырой ответ модели:\n{raw_response}")
        logger.info("Генерация текста успешна")

        clean_response = extract_last_assistant_response(full_prompt, raw_response)
        logger.info(f"Чистый ответ ассистента: {clean_response}")

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
