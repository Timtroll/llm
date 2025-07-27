# backend/controllers/models.py

import os
import glob
import subprocess
from datetime import datetime
import logging
import asyncio
from typing import Dict, Any
# from llm.backend.async_eav import AsyncEAVWithIndex

from async_eav import eav

logger = logging.getLogger(__name__)

async def list_models() -> Dict[str, Any]:
    """
    Получает список моделей из директории и синхронизирует их с EAV.
    Если модель отсутствует в EAV, добавляет её. Если модель в EAV отсутствует на диске, удаляет из EAV.
    Возвращает список моделей из EAV, если они синхронизированы, или из директории, если произошли изменения.
    """
    model_dir = "/llama.cpp/models/"
    # eav = AsyncEAVWithIndex()
    try:
        # Получаем список моделей с диска
        model_files = glob.glob(os.path.join(model_dir, "*.gguf"))
        disk_models = set(os.path.splitext(os.path.basename(file_path))[0] for file_path in model_files)
        
        # Получаем список моделей из EAV
        eav_models = set()
        # Так как AsyncEAVWithIndex не предоставляет метод для получения всех сущностей,
        # будем хранить список model_id в отдельном ключе Redis
        eav_model_ids = await eav.client.smembers("models:index")
        for model_id in eav_model_ids:
            if await eav.get_all_attributes(f"model:{model_id}"):
                eav_models.add(model_id)

        # Определяем модели для добавления и удаления
        models_to_add = disk_models - eav_models
        models_to_delete = eav_models - disk_models

        # Удаляем из EAV модели, которых нет на диске
        for model_name in models_to_delete:
            await eav.delete_entity(f"model:{model_name}")
            await eav.client.srem("models:index", model_name)
            logger.info(f"Удалена модель из EAV: {model_name}")

        # Собираем данные о моделях
        models = {}
        main_path = next(
            (p for p in [
                "/llama.cpp/build/bin/llama-cli",
                "/llama.cpp/build/llama-cli",
                "/llama.cpp/build/bin/main",
                "/llama.cpp/build/main"
            ] if os.path.isfile(p)), None
        )

        print('------==========')
        print(model_files)
        print(eav_models)
        print('------==========')

        # Если списки совпадают, читаем данные из EAV
        if disk_models == eav_models:
            models = {}
            for model_name in eav_models:
                model_data = await eav.get_all_attributes(f"model:{model_name}")
                if model_data:
                    # Преобразуем строковые значения в нужные типы
                    model_data["size"] = float(model_data["size"])
                    model_data["default_tokens"] = int(model_data["default_tokens"])
                    model_data["default_temp"] = float(model_data["default_temp"])
                    models[model_name] = model_data

        else:
            for file_path in model_files:
                model_name = os.path.splitext(os.path.basename(file_path))[0]
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Размер в МБ
                mod_time = os.path.getmtime(file_path)
                mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

                model_data = {
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

            #     # Получаем метаданные модели, если есть main_path
            #     if main_path:
            #         try:
            #             command = [main_path, "-m", file_path, "--verbose"]
            #             process = subprocess.run(command, capture_output=True, text=True, timeout=90)
            #             if process.returncode == 0:
            #                 output = process.stdout.strip()
            #                 for line in output.splitlines():
            #                     line = line.lower()
            #                     if "version" in line:
            #                         model_data["version"] = line.split(":")[-1].strip()
            #                     if "parameters" in line:
            #                         model_data["parameters"] = line.split(":")[-1].strip()
            #                     if "architecture" in line:
            #                         model_data["architecture"] = line.split(":")[-1].strip()
            #         except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            #             logger.warning(f"Не удалось получить метаданные для {model_name}: {str(e)}")

            #     # Если модель новая, добавляем в EAV
            #     if model_name in models_to_add:
            #         await eav.create_entity(f"model:{model_name}", model_data)
            #         await eav.client.sadd("models:index", model_name)
            #         logger.info(f"Добавлена модель в EAV: {model_name}")

                models[model_name] = model_data

        return models

    except Exception as e:
        logger.error(f"Ошибка при обработке моделей: {str(e)}")
        return {"error": f"Ошибка при обработке моделей: {str(e)}"}