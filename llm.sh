#!/bin/bash

# Функция для вывода текущего этапа
log_stage() {
    echo "Этап: $1"
}

# Проверка наличия Docker
if ! command -v docker > /dev/null 2>&1; then
    log_stage "Проверка наличия Docker"
    echo "Ошибка: Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверка наличия docker compose
if ! docker compose version > /dev/null 2>&1; then
    log_stage "Проверка наличия docker compose"
    echo "Ошибка: docker compose не установлен. Установите Docker Compose V2 и попробуйте снова."
    exit 1
fi

# Создание рабочей директории
# log_stage "Создание рабочей директории"
# WORK_DIR="/home/troll/sites/llm"
# echo "Создание директории: $WORK_DIR"
# mkdir -p "$WORK_DIR"
# cd "$WORK_DIR" || { echo "Не удалось перейти в $WORK_DIR"; exit 1; }

# Проверка наличия docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    log_stage "Проверка наличия docker-compose.yml"
    echo "Ошибка: Файл docker-compose.yml не найден в $WORK_DIR"
    exit 1
fi

# Список моделей
# MODELS=(
#     "llama-7b.Q4_0.gguf https://huggingface.co/TheBloke/LLaMA-7B-GGUF/resolve/main/llama-7b.Q4_0.gguf"
#     "model-q4_K.gguf https://huggingface.co/IlyaGusev/saiga_llama3_8b_gguf/resolve/main/model-q4_K.gguf"
# )

# Очистка директории WORK_DIR, сохраняя файлы из MODELS
# log_stage "Очистка рабочей директории"
# echo "Очистка директории $WORK_DIR (с сохранением файлов: ${MODELS[*]%% *})"
# EXCLUDE_FILES=("Dockerfile" "app.py" "docker-compose.yml" "*.gguf")

# FIND_EXCLUDE=""
# for model in "${MODELS[@]}"; do
#     MODEL_NAME=$(echo "$model" | awk '{print $1}')
#     if [ -z "$FIND_EXCLUDE" ]; then
#         FIND_EXCLUDE="! -name $MODEL_NAME"
#     else
#         FIND_EXCLUDE="$FIND_EXCLUDE ! -name $MODEL_NAME"
#     fi
# done

# for file in "${EXCLUDE_FILES[@]}"; do
#     FIND_EXCLUDE="$FIND_EXCLUDE ! -name '$file'"
# done

# eval "find \"$WORK_DIR\" -maxdepth 1 -type f $FIND_EXCLUDE -delete"
# if [ $? -ne 0 ]; then
#     echo "Ошибка при очистке директории $WORK_DIR"
#     exit 1
# fi

# Скачивание недостающих моделей
# log_stage "Скачивание моделей"
# for model in "${MODELS[@]}"; do
#     MODEL_FILE=$(echo "$model" | awk '{print $1}')
#     MODEL_URL=$(echo "$model" | awk '{print $2}')
#     if [ ! -f "$MODEL_FILE" ]; then
#         echo "Скачивание модели: $MODEL_URL -> $MODEL_FILE"
#         wget --progress=bar:force:noscroll "$MODEL_URL" -O "$MODEL_FILE"
#         if [ $? -ne 0 ]; then
#             echo "Ошибка при скачивании модели: $MODEL_FILE"
#             exit 1
#         fi
#         if [ ! -s "$MODEL_FILE" ]; then
#             echo "Ошибка: скачанный файл модели пустой: $MODEL_FILE"
#             exit 1
#         fi
#     else
#         echo "Модель $MODEL_FILE уже существует."
#     fi
# done

# Функция для вывода подробной справки
show_help() {
    echo "Использование: $0 {help|list|status|start-all|stop-all|rebuild-all|start <service>|stop <service>|rebuild <service>}"
    echo
    echo "Описание команд:"
    echo "  help                Выводит эту справку."
    echo "  list                Выводит список сервисов, определенных в docker-compose.yml."
    echo "  status              Показывает статус всех контейнеров из docker-compose.yml."
    echo "  start-all           Запускает все контейнеры, определенные в docker-compose.yml."
    echo "  stop-all            Останавливает все контейнеры."
    echo "  rebuild-all         Пересобирает все контейнеры."
    echo "  start <service>     Запускает указанный сервис (например, llm)."
    echo "  stop <service>      Останавливает указанный сервис."
    echo "  rebuild <service>   Пересобирает указанный сервис."
    echo
    echo "Примеры:"
    echo "  $0 list                     # Показать список сервисов"
    echo "  $0 status                   # Показать статус контейнеров"
    echo "  $0 start-all                # Запустить все контейнеры"
    echo "  $0 stop-all                 # Остановить все контейнеры"
    echo "  $0 rebuild-all              # Пересобрать все контейнеры"
    echo "  $0 start llm                # Запустить сервис llm"
    echo "  $0 stop llm                 # Остановить сервис llm"
    echo "  $0 rebuild llm              # Пересобрать сервис llm"
    echo
    echo "Дополнительно:"
    echo "  - Убедитесь, что файлы docker-compose.yml, Dockerfile и app.py существуют в $WORK_DIR."
    echo "  - Для проверки логов: docker compose logs <service> (например, docker compose logs llm)."
    echo "  - Для тестирования API (если сервис llm запущен):"
    echo "    curl -X POST http://localhost:5555/api/generate -H 'Content-Type: application/json' -d '{\"text\": \"Привет, как дела?\"}'"
}

# Функции для управления контейнерами
list_containers() {
    log_stage "Вывод списка сервисов"
    echo "Список сервисов из docker-compose.yml:"
    docker compose config --services
}

# status_containers() {
#     # log_stage "Проверка статуса контейнеров"

#     # echo "Статус контейнеров (только из docker-compose.yml):"

#     # Получаем список сервисов
#     local services=$(docker compose config --services 2>/dev/null)

#     if [[ -z "$services" ]]; then
#         echo "Нет сервисов в docker-compose.yml"
#         return 1
#     fi

#     for service in $services; do
#         # Проверяем, запущен ли контейнер для сервиса
#         if docker inspect --format='{{.State.Running}}' "$service" | jq -e '.[]' >/dev/null 2>&1; then
#             echo "✅ $service — работает"
#         else
#             echo "❌ $service — не запущен"
#         fi
#     done
# }
status_containers() {
    log_stage "Проверка статуса контейнеров"
    echo "Статус сервисов из docker-compose.yml:"

    # Получаем список сервисов
    local services=$(docker compose config --services 2>/dev/null)

    if [[ -z "$services" ]]; then
        echo "❌ Ошибка: Нет сервисов в docker-compose.yml"
        return 1
    fi

    for service in $services; do
        container="llm-$service"

        # Получаем статус через docker inspect
        status=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null)

        if [[ "$status" == "true" ]]; then
            echo "✅ $container — работает"
        elif [[ "$status" == "false" ]]; then
            echo "⚠️ $container — остановлен"
        else
            echo "❌ $container — не существует"
        fi
    done
}

start_all() {
    log_stage "Запуск всех контейнеров"
    echo "Запуск всех контейнеров..."
    docker compose up -d
    if [ $? -ne 0 ]; then
        echo "Ошибка при запуске контейнеров"
        exit 1
    fi
    echo "Все контейнеры успешно запущены"
    echo "API доступен по адресу: http://localhost:5555"
    echo "Для тестирования API выполните:"
    echo "curl -X POST http://localhost:5555/generate -H 'Content-Type: application/json' -d '{\"text\": \"Привет, как дела?\"}'"
}

stop_all() {
    log_stage "Остановка всех контейнеров"
    echo "Остановка всех контейнеров..."
    docker compose stop
    if [ $? -ne 0 ]; then
        echo "Ошибка при остановке контейнеров"
        exit 1
    fi
    echo "Все контейнеры остановлены"
}

rebuild_all() {
    log_stage "Пересборка всех контейнеров"
    echo "Пересборка всех контейнеров..."
    docker compose build
    if [ $? -ne 0 ]; then
        echo "Ошибка при пересборке контейнеров"
        exit 1
    fi
    echo "Все контейнеры пересобраны"
}

start_service() {
    local service=$1
    log_stage "Запуск сервиса $service"
    echo "Запуск сервиса $service... Комана для ручного запуска:"
    echo "docker docker compose up --build \"$service\""
    docker docker compose up --build -d "$service"
    if [ $? -ne 0 ]; then
        echo "Ошибка при запуске сервиса $service"
        exit 1
    fi
    echo "Сервис $service запущен"
}

stop_service() {
    local service=$1
    log_stage "Остановка сервиса $service"
    echo "Остановка сервиса $service..."
    docker compose stop "$service"
    if [ $? -ne 0 ]; then
        echo "Ошибка при остановке сервиса $service"
        exit 1
    fi
    echo "Сервис $service остановлен"
}

# rebuild_service() {
#     local service=$1
#     log_stage "Пересборка сервиса $service"
#     echo "Пересборка сервиса $service..."
#     docker compose build "$service"
#     if [ $? -ne 0 ]; then
#         echo "Ошибка при пересборке сервиса $service"
#         exit 1
#     fi
#     echo "Сервис $service пересобран"
# }

rebuild_service() {
    local service=$1
    log_stage "Пересборка сервиса $service"
    echo "Пересборка и перезапуск сервиса $service..."
    echo "docker compose build \"$service\""

    # 1. Пересборка сервиса
    docker compose build "$service"
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при пересборке сервиса $service"
        exit 1
    fi

    # 2. Опционально: остановка и удаление старого контейнера
    # (иногда помогает избежать конфликтов)
    docker compose down "$service" >/dev/null 2>&1

    # 3. Запуск сервиса с зависимостями
    docker compose up -d "$service"
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при запуске сервиса $service"
        exit 1
    fi

    echo "✅ Сервис $service успешно пересобран и запущен"
}

# Обработка аргументов командной строки
case "$1" in
    help)
        log_stage "Вывод справки"
        show_help
        ;;
    list)
        list_containers
        ;;
    status)
        status_containers
        ;;
    start-all)
        start_all
        ;;
    stop-all)
        stop_all
        ;;
    rebuild-all)
        rebuild_all
        ;;
    start)
        if [ -z "$2" ]; then
            echo "Ошибка: укажите имя сервиса для запуска"
            show_help
            exit 1
        fi
        start_service "$2"
        ;;
    stop)
        if [ -z "$2" ]; then
            echo "Ошибка: укажите имя сервиса для остановки"
            show_help
            exit 1
        fi
        stop_service "$2"
        ;;
    rebuild)
        if [ -z "$2" ]; then
            echo "Ошибка: укажите имя сервиса для пересборки"
            show_help
            exit 1
        fi
        rebuild_service "$2"
        ;;
    *)
        echo "Ошибка: неизвестная команда '$1'"
        show_help
        exit 1
        ;;
esac
