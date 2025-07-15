#!/bin/bash

# Примеры использования:
# Простой запуск: ./llm.sh
# Пересборка всех сервисов и запуск: ./llm.sh --rebuild
# Пересборка фронтенда и запуск: ./llm.sh --rebuild-f
# Остановка: ./llm.sh --stop
# Вывод справки: ./llm.sh --help

# Цветной вывод для улучшения UX
RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

# Определение UID и GID текущего пользователя
# CURRENT_UID=$(id -u)
# CURRENT_GID=$(id -g)
CURRENT_UID='troll'
CURRENT_GID='troll'

echo -e "Использую UID:GID = ${CURRENT_UID}:${CURRENT_GID}"

# Вывод справочной информации
print_help() {
    echo -e "${GREEN}Скрипт для управления Docker Compose с FastAPI и Next.js${RESET}"
    echo -e "\nИспользование: $0 [опции]"
    echo -e "\nОпции:"
    echo -e "  --help\t\tПоказать эту справку и выйти"
    echo -e "  --rebuild\t\tПересобрать и запустить все сервисы"
    echo -e "  --rebuild-f\t\tПересобрать и запустить только фронтенд"
    echo -e "  --stop\t\tОстановить контейнеры"
    echo -e "\nПримеры:"
    echo -e "  $0\t\t\tЗапустить или перезапустить контейнеры"
    echo -e "  $0 --rebuild\t\tПересобрать и запустить все сервисы"
    echo -e "  $0 --rebuild-f\tПересобрать и запустить фронтенд"
    echo -e "  $0 --stop\t\tОстановить контейнеры"
    echo -e "  $0 --help\t\tПоказать эту справку"
    echo -e "\nДополнительно:"
    echo -e "  Рабочая директория: WORK_DIR (по умолчанию: /home/troll/sites/llm)"
    echo -e "  API: http://localhost:5555"
    echo -e "  Frontend: http://localhost:5000"
    exit 0
}

# Проверка наличия Docker и Docker Compose
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: Docker не установлен. Установите Docker и попробуйте снова.${RESET}"
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: Docker-демон не запущен. Запустите Docker и попробуйте снова.${RESET}"
        exit 1
    fi
    if ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: Docker Compose не установлен. Установите Docker Compose и попробуйте снова.${RESET}"
        exit 1
    fi
}

# Проверка наличия openssl
# check_openssl() {
#     if ! command -v openssl >/dev/null 2>&1; then
#         echo -e "${GREEN}Установка openssl...${RESET}"
#         if ! sudo apt update -y >/dev/null 2>&1 || ! sudo apt install -y openssl >/dev/null 2>&1; then
#             echo -e "${RED}Ошибка: Не удалось установить openssl. Попробуйте установить вручную: sudo apt install openssl${RESET}"
#         fi
#     fi
# }

# Проверка наличия docker-compose.yml
check_docker_compose_file() {
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}Ошибка: docker-compose.yml не найден${RESET}"
        exit 1
    fi
}

# Проверка наличия package-lock.json
check_package_lock() {
    if [ ! -f "frontend/package-lock.json" ]; then
        echo -e "${RED}Ошибка: frontend/package-lock.json не найден. Создайте его с помощью 'npm install' в директории frontend.${RESET}"
        exit 1
    fi
}

# Проверка и создание .env файлов
# setup_env_files() {
#     # Генерация JWT_SECRET
#     if command -v openssl >/dev/null 2>&1; then
#         JWT_SECRET=$(openssl rand -base64 32)
#     else
#         JWT_SECRET=$(head -c 32 /dev/urandom | base64)
#     fi
#     if [ -z "$JWT_SECRET" ]; then
#         echo -e "${RED}Ошибка: Не удалось сгенерировать JWT_SECRET${RESET}"
#         exit 1
#     fi

#     # Создание frontend/.env.local
#     ENV_FILE="frontend/.env.local"
#     if [ ! -f "$ENV_FILE" ] || ! grep -q "JWT_SECRET=" "$ENV_FILE"; then
#         echo -e "${GREEN}Создание или обновление $ENV_FILE...${RESET}"
#         mkdir -p frontend
#         cat <<EOL > "$ENV_FILE"
# JWT_SECRET=$JWT_SECRET
# NEXT_PUBLIC_API_URL=http://llm:5555
# PORT=5000
# EOL
#         chmod 600 "$ENV_FILE"
#         chown troll:troll "$ENV_FILE"
#     else
#         echo -e "${GREEN}$ENV_FILE уже существует и содержит JWT_SECRET.${RESET}"
#     fi

#     # Создание llm/.env
#     LLM_ENV_FILE="llm/.env"
#     if [ ! -f "$LLM_ENV_FILE" ] || ! grep -q "JWT_SECRET=" "$LLM_ENV_FILE"; then
#         echo -e "${GREEN}Создание или обновление $LLM_ENV_FILE...${RESET}"
#         mkdir -p llm
#         cat <<EOL > "$LLM_ENV_FILE"
# JWT_SECRET=$JWT_SECRET
# EOL
#         chmod 600 "$LLM_ENV_FILE"
#         chown troll:troll "$LLM_ENV_FILE"
#     else
#         echo -e "${GREEN}$LLM_ENV_FILE уже существует и содержит JWT_SECRET.${RESET}"
#     fi

#     # Проверка согласованности JWT_SECRET
#     FRONTEND_JWT=$(grep JWT_SECRET "$ENV_FILE" | cut -d '=' -f 2)
#     LLM_JWT=$(grep JWT_SECRET "$LLM_ENV_FILE" | cut -d '=' -f 2)
#     if [ "$FRONTEND_JWT" != "$LLM_JWT" ]; then
#         echo -e "${RED}Ошибка: JWT_SECRET в $ENV_FILE и $LLM_ENV_FILE не совпадают${RESET}"
#         exit 1
#     fi
# }

# Проверка и установка прав файлов
# setup_permissions() {
#     echo "Установка прав доступа для файлов..."
#     find . -not -path "./node_modules/*" -not -path "./frontend/.next/*" -exec chmod u=rwX,go=rX {} \;
#     find . -not -path "./node_modules/*" -not -path "./frontend/.next/*" -exec chown troll:troll {} \;
#     [ -f "frontend/.env.local" ] && chmod 600 frontend/.env.local && chown troll:troll frontend/.env.local
#     [ -f "llm/.env" ] && chmod 600 llm/.env && chown troll:troll llm/.env
# }
setup_permissions() {
    echo "Установка прав доступа для файлов..."
    find . -not -path "./node_modules/*" -not -path "./frontend/.next/*" -exec chmod u=rwX,go=rX {} \;
    find . -not -path "./node_modules/*" -not -path "./frontend/.next/*" -exec chown "${CURRENT_UID}:${CURRENT_GID}" {} \;
    [ -f "frontend/.env.local" ] && chmod 600 frontend/.env.local && chown "${CURRENT_UID}:${CURRENT_GID}" frontend/.env.local
    [ -f "llm/.env" ] && chmod 600 llm/.env && chown "${CURRENT_UID}:${CURRENT_GID}" llm/.env
}

# Обработка аргументов
parse_args() {
    REBUILD=0
    REBUILD_FRONTEND=0
    STOP=0
    for arg in "$@"; do
        case "$arg" in
            --help) print_help ;;
            --rebuild) REBUILD=1 ;;
            --rebuild-f) REBUILD_FRONTEND=1 ;;
            --stop) STOP=1 ;;
            *) echo -e "${RED}Ошибка: Неизвестный аргумент '$arg'. Допустимые: --help, --rebuild, --rebuild-f, --stop${RESET}"; exit 1 ;;
        esac
    done
    if [ "$REBUILD" -eq 1 ] && [ "$STOP" -eq 1 ]; then
        echo -e "${RED}Ошибка: Нельзя использовать --rebuild и --stop одновременно.${RESET}"
        exit 1
    fi
    if [ "$REBUILD_FRONTEND" -eq 1 ] && [ "$STOP" -eq 1 ]; then
        echo -e "${RED}Ошибка: Нельзя использовать --rebuild-f и --stop одновременно.${RESET}"
        exit 1
    fi
    if [ "$REBUILD" -eq 1 ] && [ "$REBUILD_FRONTEND" -eq 1 ]; then
        echo -e "${RED}Ошибка: Нельзя использовать --rebuild и --rebuild-f одновременно.${RESET}"
        exit 1
    fi
    export REBUILD REBUILD_FRONTEND STOP
}

# Получение текущей директории
setup_work_dir() {
    WORK_DIR="${WORK_DIR:-/home/troll/sites/llm}"
    echo "Создание директории: $WORK_DIR"
    if ! mkdir -p "$WORK_DIR"; then
        echo -e "${RED}Ошибка: Не удалось создать $WORK_DIR${RESET}"
        exit 1
    fi
    if [ ! -w "$WORK_DIR" ]; then
        echo -e "${RED}Ошибка: Нет прав на запись в $WORK_DIR${RESET}"
        exit 1
    fi
    export WORK_DIR
}

# Скачивание моделей
download_models() {
    cd "$WORK_DIR" || exit 1
    MODELS=(
        "grock-3.gguf https://huggingface.co/mradermacher/Grok-3-reasoning-gemma3-4B-distilled-HF-GGUF/resolve/main/Grok-3-reasoning-gemma3-4B-distilled-HF.Q8_0.gguf?download=true"
        "gpt-4o.gguf https://huggingface.co/mradermacher/oh-dcft-v3.1-gpt-4o-mini-GGUF?show_file_info=oh-dcft-v3.1-gpt-4o-mini.Q2_K.gguf"
        "model-q4_K.gguf https://huggingface.co/IlyaGusev/saiga_llama3_8b_gguf/resolve/main/model-q4_K.gguf"
    )

    for model in "${MODELS[@]}"; do
        MODEL_FILE=$(echo "$model" | awk '{print $1}')
        MODEL_URL=$(echo "$model" | awk '{print $2}')
        if [ ! -f "$MODEL_FILE" ]; then
            echo "Скачивание модели: $MODEL_URL -> $MODEL_FILE"
            if ! wget --progress=bar:force:noscroll --timeout=30 "$MODEL_URL" -O "$MODEL_FILE"; then
                echo -e "${RED}Ошибка при скачивании модели: $MODEL_FILE${RESET}"
                exit 1
            fi
            if [ ! -s "$MODEL_FILE" ]; then
                echo -e "${RED}Ошибка: Скачанный файл модели пустой: $MODEL_FILE${RESET}"
                exit 1
            fi
        else
            echo "Модель $MODEL_FILE уже существует."
        fi
    done
}

# Проверка состояния контейнеров
check_containers() {
    if docker compose ps | grep -q "Up"; then
        echo "Контейнеры запущены."
        if [ "$REBUILD" -eq 1 ]; then
            echo "Остановка и удаление всех контейнеров..."
            if ! docker compose down >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнеров${RESET}"
                exit 1
            fi
        elif [ "$REBUILD_FRONTEND" -eq 1 ]; then
            echo "Остановка и пересборка фронтенда..."
            if ! docker compose rm -f nextjs >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при удалении контейнера nextjs${RESET}"
                exit 1
            fi
            if ! docker compose build nextjs >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при сборке фронтенда. Проверьте логи: docker compose logs nextjs${RESET}"
                exit 1
            fi
            if ! docker compose up -d nextjs >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при запуске фронтенда. Проверьте логи: docker compose logs nextjs${RESET}"
                exit 1
            fi
            check_api_availability
            print_instructions
            exit 0
        elif [ "$STOP" -eq 1 ]; then
            echo "Остановка контейнеров..."
            if ! docker compose stop >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнеров${RESET}"
                exit 1
            fi
            exit 0
        else
            echo "Перезапуск контейнеров..."
            if ! docker compose restart >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при перезапуске контейнеров. Проверьте логи: docker compose logs${RESET}"
                exit 1
            fi
            check_api_availability
            print_instructions
            exit 0
        fi
    else
        echo "Контейнеры не запущены."
        if [ "$STOP" -eq 1 ]; then
            echo "Остановка контейнеров..."
            if ! docker compose stop >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнеров${RESET}"
                exit 1
            fi
            exit 0
        fi
    fi
}

# Сборка и запуск контейнеров
build_and_run_containers() {
    check_docker_compose_file
    if [ "$REBUILD" -eq 1 ]; then
        echo "Сборка и запуск всех контейнеров..."
        echo `pwd`
        echo "docker compose up -d"
        # if ! docker compose up -d --build >/dev/null 2>&1; then
        if ! docker compose up -d --build; then
            echo -e "${RED}Ошибка при сборке или запуске контейнеров. Проверьте логи: docker compose logs${RESET}"
            exit 1
        fi
    elif [ "$REBUILD_FRONTEND" -eq 1 ]; then
        check_package_lock
        echo "Сборка и запуск фронтенда..."
        if ! docker compose build nextjs >/dev/null 2>&1; then
            echo -e "${RED}Ошибка при сборке фронтенда. Проверьте логи: docker compose logs nextjs${RESET}"
            exit 1
        fi
        if ! docker compose up -d nextjs >/dev/null 2>&1; then
            echo -e "${RED}Ошибка при запуске фронтенда. Проверьте логи: docker compose logs nextjs${RESET}"
            exit 1
        fi
    else
        echo "Запуск контейнеров..."
        if ! docker compose up -d >/dev/null 2>&1; then
            echo -e "${RED}Ошибка при запуске контейнеров. Проверьте логи: docker compose logs${RESET}"
            exit 1
        fi
    fi
}

# Проверка доступности API
check_api_availability() {
    sleep 3
    if nc -z localhost 5555 >/dev/null 2>&1; then
        echo -e "${GREEN}API успешно запущен и доступен по адресу: http://localhost:5555${RESET}"
    else
        echo -e "${RED}Внимание: API на http://localhost:5555 недоступен. Проверьте логи: docker compose logs llm${RESET}"
    fi
    if nc -z localhost 5000 >/dev/null 2>&1; then
        echo -e "${GREEN}Frontend успешно запущен и доступен по адресу: http://localhost:5000${RESET}"
    else
        echo -e "${RED}Внимание: Frontend на http://localhost:5000 недоступен. Проверьте логи: docker compose logs nextjs${RESET}"
    fi
}

# Вывод инструкций
print_instructions() {
    echo -e "\nДля тестирования API выполните:"
    echo "curl -X POST http://localhost:5555/generate -H 'Content-Type: application/json' -H 'Authorization: Bearer <your-jwt-token>' -d '{\"text\": \"Привет, как дела?\", \"session_id\": \"default\"}'"
    echo "Для доступа к фронтенду: http://localhost:5000"
    echo "Для проверки логов: docker compose logs"
    echo "Для остановки контейнеров: docker compose stop"
    echo "Для удаления контейнеров: docker compose down"
}

echo -e "---------"

# Основной код
check_docker
# check_openssl
setup_work_dir
cd "$WORK_DIR" || exit 1

# setup_env_files
setup_permissions
parse_args "$@"
download_models
check_containers
build_and_run_containers
check_api_availability
print_instructions
