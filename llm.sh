#!/bin/bash

# Примеры использования:
# Простой запуск: ./llm.sh
# Пересборка и запуск: ./llm.sh --rebuild
# Остановка: ./llm.sh --stop
# Вывод справки: ./llm.sh --help

# Цветной вывод для улучшения UX
RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

# Вывод справочной информации
print_help() {
    echo -e "${GREEN}Скрипт для управления Docker Compose с FastAPI и Next.js${RESET}"
    echo -e "\nИспользование: $0 [опции]"
    echo -e "\nОпции:"
    echo -e "  --help\t\tПоказать эту справку и выйти"
    echo -e "  --rebuild\t\tПересобрать и запустить контейнеры"
    echo -e "  --stop\t\tОстановить контейнеры"
    echo -e "\nПримеры:"
    echo -e "  $0\t\t\tЗапустить или перезапустить контейнеры"
    echo -e "  $0 --rebuild\t\tПересобрать образы и запустить контейнеры"
    echo -e "  $0 --stop\t\tОстановить контейнеры"
    echo -e "  $0 --help\t\tПоказать эту справку"
    echo -e "\nДополнительно:"
    echo -e "  Рабочая директория задается через переменную окружения WORK_DIR (по умолчанию: /home/troll/sites/llm)"
    echo -e "  API доступен по адресу: http://localhost:5555"
    echo -e "  Frontend доступен по адресу: http://localhost:5000"
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

# Обработка аргументов
parse_args() {
    REBUILD=0
    STOP=0
    for arg in "$@"; do
        case "$arg" in
            --help) print_help ;;
            --rebuild) REBUILD=1 ;;
            --stop) STOP=1 ;;
            *) echo -e "${RED}Ошибка: Неизвестный аргумент '$arg'. Допустимые: --help, --rebuild, --stop${RESET}"; exit 1 ;;
        esac
    done
    if [ "$REBUILD" -eq 1 ] && [ "$STOP" -eq 1 ]; then
        echo -e "${RED}Ошибка: Нельзя использовать --rebuild и --stop одновременно.${RESET}"
        exit 1
    fi
    export REBUILD STOP
}

# Получение текущей директории
setup_work_dir() {
    WORK_DIR="${WORK_DIR:-$(pwd)}"
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
        # "llama-7b.Q4_0.gguf https://huggingface.co/TheBloke/LLaMA-7B-GGUF/resolve/main/llama-7b.Q4_0.gguf"
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
            echo "Остановка и удаление контейнеров..."
            if ! docker compose down >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнеров${RESET}"
                exit 1
            fi
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
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}Ошибка: docker-compose.yml не найден${RESET}"
        exit 1
    fi
    if [ "$REBUILD" -eq 1 ]; then
        echo "Сборка и запуск контейнеров..."
        if ! docker compose up -d --build; then
            echo -e "${RED}Ошибка при сборке или запуске контейнеров. Проверьте логи: docker compose logs${RESET}"
            exit 1
        fi
    else
        echo "Запуск контейнеров..."
        if ! docker compose up -d; then
            echo -e "${RED}Ошибка при запуске контейнеров. Проверьте логи: docker compose logs${RESET}"
            exit 1
        fi
    fi
}

# Проверка доступности API
check_api_availability() {
    sleep 2
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
    echo "curl -X POST http://localhost:5555/generate -H 'Content-Type: application/json' -d '{\"text\": \"Привет, как дела?\"}'"
    echo "Для доступа к фронтенду: http://localhost:5000"
    echo "Для проверки логов: docker compose logs"
    echo "Для остановки контейнеров: docker compose stop"
    echo "Для удаления контейнеров: docker compose down"
}

# Основной код
check_docker
setup_work_dir
parse_args "$@"
download_models
check_containers
build_and_run_containers
check_api_availability
print_instructions
