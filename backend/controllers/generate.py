# backend/controllers/generate.py

import os
import re
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any

from controllers.models import list_models
from async_eav import eav

logger = logging.getLogger(__name__)

async def generate_text(
        prompt: Dict[str, Any],
        current_user: dict
) -> Dict[str, Any]:
    
    # Конфигурация моделей
    MODELS_CONFIG = await list_models()

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

        assistant_response = {
            "role": "assistant",
            "content": clean_response,
            "timestamp": datetime.utcnow().isoformat()
        }
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


def extract_assistant_response(raw_response: str) -> str:
    result = ""
    match = re.search(r"assistant\s*(.*?)\s*> EOF by user", raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        result = match.group(1).strip()
    return result
