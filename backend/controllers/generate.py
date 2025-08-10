# backend/controllers/generate.py

import os
import re
import json
import subprocess
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from controllers.models import list_models
from async_eav import eav
from settings import settings

ACCESS_TOKEN_EXPIRE = settings.access_token_expire
# Глобальная настройка поиска
SEARCH_ENABLED = os.getenv("SEARCH_ENABLED", "true").lower() == "true"

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def estimate_tokens_smart(text: Union[str, List[int]]) -> int:
    """
    Оценивает количество токенов в тексте или списке токенов.
    
    Args:
        text: Текст или список токенов.
    
    Returns:
        Примерное количество токенов.
    """
    if isinstance(text, list):
        return len(text)
    
    if not isinstance(text, str):
        text = str(text)
    
    if not text:
        return 0
    
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', text))
    total_chars = len(text)
    
    ratio = cyrillic_chars / total_chars if total_chars else 0
    coef = 3.3 if ratio > 0.7 else 4.0 if ratio < 0.3 else 3.6
    return int(total_chars / coef)


def build_prompt(messages: List[Dict[str, Any]]) -> str:
    """
    Формирует prompt из списка сообщений.
    
    Args:
        messages: Список сообщений с ролями и содержимым.
    
    Returns:
        Строковый prompt для модели.
    """
    system_prompt = (
        "Ты — русскоязычный помощник. Отвечай строго на русском языке, лаконично, понятно и в формате Markdown.\n"
    )
    prompt = system_prompt
    for msg in sorted(messages, key=lambda m: m.get("timestamp", "")):
        role = msg.get("role")
        content = msg.get("content", "").strip()
        prompt += f"<|{role}|>{content}\n"
    return prompt.strip()


def find_executable() -> Optional[str]:
    """
    Ищет исполняемый файл llama.cpp.
    
    Returns:
        Путь к исполняемому файлу или None, если не найден.
    """
    possible_paths = [
        "/llama.cpp/build/bin/llama-cli",
        "/llama.cpp/build/llama-cli",
        "/llama.cpp/build/bin/main",
        "/llama.cpp/build/main"
    ]
    return next((p for p in possible_paths if os.path.isfile(p)), None)


def build_command(main_path: str, model_config: Dict[str, Any], prompt_text: str, params: Dict) -> List[str]:
    """
    Формирует команду для запуска модели.
    
    Args:
        main_path: Путь к исполняемому файлу.
        model_config: Конфигурация модели.
        prompt_text: Текст prompt'а.
        params: Параметры генерации.
    
    Returns:
        Список аргументов команды.
    """
    command = [
        main_path,
        "-m", model_config["path"],
        "-p", prompt_text,
        "-n", str(params.get("n_tokens", model_config.get("default_tokens", 512))),
        "--temp", str(params.get("temperature", model_config.get("default_temp", 0.7))),
        "-cnv"
    ]
    optional_params = [
        ("top_p", "--top-p"),
        ("top_k", "--top-k"),
        ("repeat_penalty", "--repeat-penalty"),
        ("seed", "--seed")
    ]
    for param, flag in optional_params:
        if params.get(param) is not None:
            command.extend([flag, str(params[param])])
    
    return command


def extract_assistant_response(raw_output: str, prompt_text: str) -> str:
    """
    Извлекает ответ модели из сырого вывода, учитывая формат с начальной строкой 'user' и маркером '> EOF by user'.
    
    Args:
        raw_output: Сырой вывод команды.
        prompt_text: Исходный prompt (включает системный prompt и сообщения пользователя).
    
    Returns:
        Ответ модели или пустая строка в случае ошибки.
    """
    try:
        print(f"Исходный prompt: {prompt_text}")
        print(f"Сырой вывод: {raw_output}")

        # Удаляем начальную строку 'user' и пустые строки до текста prompt'а
        lines = raw_output.splitlines()
        response_lines = lines
        if response_lines and response_lines[0].strip() == "user":
            response_lines = response_lines[1:]  # Пропускаем строку 'user'

        # Собираем текст обратно
        response = "\n".join(response_lines).strip()

        # Экранируем prompt_text для regex
        escaped_prompt = re.escape(prompt_text)
        # Удаляем prompt из вывода
        response = re.sub(rf"^{escaped_prompt}\s*", "", response, count=1, flags=re.DOTALL).strip()

        # Удаляем технические метаданные ([LOG], ===)
        lines = response.splitlines()
        filtered_lines = [line for line in lines if not line.startswith(("[LOG]", "==="))]
        response = "\n".join(filtered_lines).strip()

        # Извлекаем ответ модели, начиная с первой строки после prompt'а до '> EOF by user'
        match = re.search(r".*?assistant\s*(.*?)\s*> EOF by user\s*$", response, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1).strip()
        else:
            result = response.strip()

        # Удаляем специальные токены, если они есть
        result = re.sub(r"<\|.*?\|>", "", result).strip()

        # Если ответ начинается с Markdown-формата (например, ###), считаем это началом ответа
        if result.startswith("###"):
            result = result.strip()

        print(f"Извлеченный ответ: {result}")
        return result

    except Exception as e:
        logger.error(f"Ошибка при извлечении ответа: {str(e)}", exc_info=True)
        return ""


async def save_user_message(text: str, history_key: str, eav) -> None:
    """
    Сохраняет сообщение пользователя в EAV хранилище.
    
    Args:
        text: Текст сообщения.
        history_key: Ключ истории.
        eav: Объект для работы с EAV хранилищем.
    """
    timestamp = datetime.utcnow().isoformat()
    user_message = {
        "role": "user",
        "content": text,
        "timestamp": timestamp
    }
    await eav.set_attribute(
        history_key,
        f"message:{timestamp}",
        json.dumps(user_message, ensure_ascii=False),
        ttl=ACCESS_TOKEN_EXPIRE
    )


async def save_assistant_response(response: str, history_key: str, eav) -> None:
    """
    Сохраняет ответ модели в EAV хранилище.
    
    Args:
        response: Ответ модели.
        history_key: Ключ истории.
        eav: Объект для работы с EAV хранилищем.
    """
    timestamp = datetime.utcnow().isoformat()
    assistant_message = {
        "role": "assistant",
        "content": response,
        "timestamp": timestamp
    }
    await eav.set_attribute(
        history_key,
        f"message:{timestamp}",
        json.dumps(assistant_message, ensure_ascii=False),
        ttl=ACCESS_TOKEN_EXPIRE
    )


async def clear_previous_assistant_messages(history_key: str, eav) -> None:
    """
    Удаляет предыдущие сообщения ассистента из EAV хранилища.
    
    Args:
        history_key: Ключ истории.
        eav: Объект для работы с EAV хранилищем.
    """
    history_data = await eav.get_all_attributes(history_key)
    for key, value in history_data.items():
        msg = json.loads(value)
        if msg.get("role") == "assistant":
            await eav.delete_attribute(history_key, key)


async def search_internet(query: str) -> str:
    """
    Выполняет поиск в интернете через API DuckDuckGo.
    
    Args:
        query: Поисковый запрос.
    
    Returns:
        Результат поиска или сообщение об ошибке.
    """
    if not SEARCH_ENABLED:
        logger.info("Поиск в интернете отключен")
        return "Поиск в интернете отключен."
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1}
            )
            data = response.json()
            result = data.get("Abstract") or (
                data.get("RelatedTopics", [{}])[0].get("Text", "Ничего не найдено.")
            )
            logger.info(f"Результат поиска: {result}")
            return result
    except Exception as e:
        logger.error(f"Ошибка поиска в интернете: {str(e)}", exc_info=True)
        return "Ошибка при попытке поиска в интернете."


async def generate_text(prompt: Dict[str, Any], current_user: dict) -> Dict[str, Any]:
    """
    Обрабатывает запрос пользователя, вызывает модель и возвращает ответ.
    
    Args:
        prompt: Словарь с запросом пользователя.
        current_user: Данные текущего пользователя.
    
    Returns:
        Словарь с ответом модели, историей и параметрами или ошибкой.
    """
    try:
        # Валидация входных данных
        if "text" not in prompt:
            logger.error("Поле 'text' отсутствует в запросе")
            return {"error": "Поле 'text' обязательно в запросе"}
        
        # Инициализация сессии
        session_id = prompt.get("session_id", f"user:{current_user['username']}")
        history_key = f"history:{current_user['username']}:{session_id}"
        
        if prompt.get("reset"):
            await eav.delete_entity(history_key)
            logger.info(f"История для сессии {session_id} очищена")
        
        # Очистка пользовательского ввода
        text_input = re.sub(r"<\|.*?\|>", "", prompt["text"]).strip()
        
        # Поиск в интернете, если включен
        if prompt.get("use_search", False):
            internet_info = await search_internet(text_input)
            text_input += f"\n\n<%info%>Информация из интернета: {internet_info}<%info%>"
        
        # Загрузка конфигурации моделей
        models_config = await list_models(current_user)
        model_name = prompt.get("model", list(models_config.keys())[0])
        model_config = models_config.get(model_name)
        if not model_config:
            logger.error(f"Модель '{model_name}' не найдена")
            return {"error": f"Модель '{model_name}' не найдена"}
        
        # Подсчет токенов в пользовательском вводе
        token_count = estimate_tokens_smart(text_input)
        max_tokens = model_config.get("max_tokens", 2048)
        logger.info(f"Количество токенов в пользовательском вводе: {token_count}")
        if token_count > max_tokens:
            logger.error(f"Превышен лимит токенов: {token_count} > {max_tokens}")
            return {"error": f"Превышен лимит токенов: {token_count} > {max_tokens}"}
        
        # Сохранение пользовательского сообщения
        await save_user_message(text_input, history_key, eav)
        
        # Загрузка истории
        history_data = await eav.get_all_attributes(history_key)
        messages_raw = [
            json.loads(value)
            for key, value in sorted(history_data.items())
            if key.startswith("message:")
        ]
        
        # Формирование prompt'а
        prompt_text = build_prompt(messages_raw)
        prompt_token_count = estimate_tokens_smart(prompt_text)
        logger.info(f"Количество токенов в полном prompt: {prompt_token_count}")
        if prompt_token_count > max_tokens:
            logger.error(f"Превышен лимит токенов в полном prompt: {prompt_token_count} > {max_tokens}")
            return {"error": f"Превышен лимит токенов в полном prompt: {prompt_token_count} > {max_tokens}"}
        
        # Формирование параметров
        params = {
            "n_tokens": prompt.get("n_tokens", model_config.get("default_tokens", 512)),
            "temperature": prompt.get("temp", model_config.get("default_temp", 0.7)),
            "top_p": prompt.get("top_p"),
            "top_k": prompt.get("top_k"),
            "repeat_penalty": prompt.get("repeat_penalty"),
            "seed": prompt.get("seed")
        }
        
        # Поиск исполняемого файла
        main_path = find_executable()
        if not main_path:
            logger.error("Исполняемый файл llama.cpp не найден")
            return {"error": "Не найден исполняемый файл llama.cpp"}
        
        # Формирование и выполнение команды
        command = build_command(main_path, model_config, prompt_text, params)
        logger.info(f"Команда запуска: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды: {result.stderr}")
            return {"error": f"Ошибка выполнения: {result.stderr}"}
        
        # Извлечение ответа
        assistant_response = extract_assistant_response(result.stdout, prompt_text)
        if not assistant_response:
            logger.error("Не удалось извлечь ответ модели")
            return {"error": "Не удалось извлечь ответ модели"}
        
        # Подсчет токенов в ответе
        response_token_count = estimate_tokens_smart(assistant_response)
        logger.info(f"Количество токенов в ответе: {response_token_count}")
        
        # Удаление старых сообщений ассистента
        await clear_previous_assistant_messages(history_key, eav)
        
        # Сохранение ответа
        await save_assistant_response(assistant_response, history_key, eav)
        
        # Формирование истории
        history_data = await eav.get_all_attributes(history_key)
        messages = [
            json.loads(value)
            for key, value in sorted(history_data.items())
            if key.startswith("message:")
        ]
        history = build_prompt(messages)
        
        return {
            "session_id": session_id,
            "model": model_name,
            "history": history.strip(),
            "response": assistant_response,
            "parameters": params
        }
    
    except subprocess.TimeoutExpired:
        logger.error("Превышено время ожидания генерации")
        return {"error": "Превышено время ожидания генерации"}
    except Exception as e:
        logger.error(f"Ошибка при генерации: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при генерации: {str(e)}"}


async def clear_history(current_user: dict) -> Dict[str, Any]:
    """
    Очищает историю запросов и ответов AI для текущего пользователя.
    
    Args:
        current_user: Данные текущего пользователя.
    
    Returns:
        Словарь с результатом операции.
    """
    try:
        session_id = f"user:{current_user['username']}"
        print(f"session_id = {session_id}")
        history_key = f"history:{current_user['username']}"
        print(f"history_key = {history_key}")
        await eav.delete_entity(history_key)
        logger.info(f"История для пользователя {current_user['username']} очищена")
        return {"message": "История успешно очищена"}
    except Exception as e:
        logger.error(f"Ошибка при очистке истории для {current_user['username']}: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при очистке истории: {str(e)}"}
