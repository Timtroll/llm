#!/bin/bash

# Примеры использования:
# Простой запуск FastAPI: ./llm.sh
# Пересборка и запуск контейнера с volume: ./llm.sh --rebuild
# Остановка контейнера: ./llm.sh --stop

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "Ошибка: Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Создание рабочей директории
WORK_DIR="/home/troll/sites/llm"
echo "Создание директории: $WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR" || { echo "Не удалось перейти в $WORK_DIR"; exit 1; }

# Проверка аргументов
REBUILD=0
STOP=0
for arg in "$@"; do
    if [ "$arg" == "--rebuild" ]; then
        REBUILD=1
    elif [ "$arg" == "--stop" ]; then
        STOP=1
    fi
done

# Список моделей и их URL
MODELS=(
    "llama-7b.Q4_0.gguf https://huggingface.co/TheBloke/LLaMA-7B-GGUF/resolve/main/llama-7b.Q4_0.gguf"
    "model-q4_K.gguf https://huggingface.co/IlyaGusev/saiga_llama3_8b_gguf/resolve/main/model-q4_K.gguf"
)

# Скачиваем недостающие модели
for model in "${MODELS[@]}"; do
    MODEL_FILE=$(echo "$model" | awk '{print $1}')
    MODEL_URL=$(echo "$model" | awk '{print $2}')

    if [ ! -f "$MODEL_FILE" ]; then
        echo "Скачивание модели: $MODEL_URL -> $MODEL_FILE"
        wget --progress=bar:force:noscroll "$MODEL_URL" -O "$MODEL_FILE"
        if [ $? -ne 0 ]; then
            echo "Ошибка при скачивании модели: $MODEL_FILE"
            exit 1
        fi
        # Проверка, что файл не пустой
        if [ ! -s "$MODEL_FILE" ]; then
            echo "Ошибка: скачанный файл модели пустой: $MODEL_FILE"
            exit 1
        fi
    else
        echo "Модель $MODEL_FILE уже существует."
    fi
done

# Проверка существования контейнера
if docker ps -a --format '{{.Names}}' | grep -q '^llm-container$'; then
    echo "Контейнер llm-container найден."
    if [ $REBUILD -eq 1 ]; then
        echo "Остановка и удаление контейнера llm-container..."
        docker stop llm-container >/dev/null 2>&1
        docker rm llm-container >/dev/null 2>&1
    elif [ $STOP -eq 1 ]; then
        echo "Остановка контейнера llm-container..."
        docker stop llm-container >/dev/null 2>&1
    else
        echo "Перезапуск контейнера llm-container..."
        docker restart llm-container
        if [ $? -ne 0 ]; then
            echo "Ошибка при перезапуске контейнера. Проверьте логи: docker logs llm-container"
            exit 1
        fi
        echo "Контейнер успешно перезапущен. API доступен по адресу: http://localhost:5555"
        echo "Проверка логов: docker logs llm-container"
        exit 0
    fi
else
    echo "Контейнер llm-container не найден. Требуется пересборка."
    REBUILD=1
fi

# Пересборка и запуск контейнера
if [ $REBUILD -eq 1 ]; then
    echo "Сборка Docker-образа llm-api..."
    docker build -t llm-api .
    if [ $? -ne 0 ]; then
        echo "Ошибка при сборке Docker-образа. Проверьте логи выше."
        exit 1
    fi
fi

echo "Запуск Docker-контейнера llm-container с монтированием моделей из $WORK_DIR в /llama.cpp/models..."
docker run -d -p 5555:5555 -v "$WORK_DIR:/llama.cpp/models" --name llm-container llm-api
if [ $? -ne 0 ]; then
    echo "Ошибка при запуске контейнера. Проверьте логи: docker logs llm-container"
    exit 1
fi
echo "Контейнер успешно запущен. API доступен по адресу: http://localhost:5555"

# Инструкции для проверки
echo "Для тестирования API выполните:"
echo "curl -X POST http://localhost:5555/generate -H 'Content-Type: application/json' -d '{\"text\": \"Привет, как дела?\"}'"
echo "Для проверки логов: docker logs llm-container"
echo "Для остановки контейнера: docker stop llm-container"
echo "Для удаления контейнера: docker rm llm-container"