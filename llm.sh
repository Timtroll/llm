#!/bin/bash

# Примеры использования:
# Простой запуск FastAPI: ./llm.sh
# Пересборка и запуск контейнера с volume: ./llm.sh --rebuild
# Остановка контейнера: ./llm.sh --stop
# Вывод справки: ./llm.sh --help

# Цветной вывод для улучшения UX
RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

# Вывод справочной информации
print_help() {
    echo -e "${GREEN}Скрипт для управления Docker-контейнером с FastAPI и моделями машинного обучения${RESET}"
    echo -e "\nИспользование: $0 [опции]"
    echo -e "\nОпции:"
    echo -e "  --help\t\tПоказать эту справку и выйти"
    echo -e "  --rebuild\t\tПересобрать и запустить контейнер с монтированием директории моделей"
    echo -e "  --stop\t\tОстановить контейнер"
    echo -e "\nПримеры:"
    echo -e "  $0\t\t\tЗапустить или перезапустить контейнер"
    echo -e "  $0 --rebuild\t\tПересобрать образ и запустить новый контейнер"
    echo -e "  $0 --stop\t\tОстановить существующий контейнер"
    echo -e "  $0 --help\t\tПоказать эту справку"
    echo -e "\nДополнительно:"
    echo -e "  Рабочая директория задается через переменную окружения WORK_DIR (по умолчанию: /home/troll/sites/llm)"
    echo -e "  API доступен по адресу: http://localhost:5555 после успешного запуска"
    exit 0
}

# Проверка наличия Docker и демона
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: Docker не установлен. Установите Docker и попробуйте снова.${RESET}"
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: Docker-демон не запущен. Запустите Docker и попробуйте снова.${RESET}"
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

# Создание и проверка рабочей директории
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
    if ! cd "$WORK_DIR"; then
        echo -e "${RED}Ошибка: Не удалось перейти в $WORK_DIR${RESET}"
        exit 1
    fi
    export WORK_DIR
}

# Скачивание моделей
download_models() {
    MODELS=(
        "llama-7b.Q4_0.gguf https://huggingface.co/TheBloke/LLaMA-7B-GGUF/resolve/main/llama-7b.Q4_0.gguf"
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

# Проверка состояния контейнера
check_container() {
    if docker ps -a --format '{{.Names}} {{.Status}}' | grep -q '^llm-container.*Up'; then
        echo "Контейнер llm-container запущен."
        if [ "$REBUILD" -eq 1 ]; then
            echo "Остановка и удаление контейнера llm-container..."
            if ! docker stop llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнера${RESET}"
                exit 1
            fi
            if ! docker rm llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при удалении контейнера${RESET}"
                exit 1
            fi
        elif [ "$STOP" -eq 1 ]; then
            echo "Остановка контейнера llm-container..."
            if ! docker stop llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнера${RESET}"
                exit 1
            fi
            exit 0
        else
            echo "Перезапуск контейнера llm-container..."
            if ! docker restart llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при перезапуске контейнера. Проверьте логи: docker logs llm-container${RESET}"
                exit 1
            fi
            check_api_availability
            print_instructions
            exit 0
        fi
    elif docker ps -a --format '{{.Names}}' | grep -q '^llm-container'; then
        echo "Контейнер llm-container существует, но не запущен."
        if [ "$STOP" -eq 1 ]; then
            echo "Остановка контейнера llm-container..."
            if ! docker stop llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при остановке контейнера${RESET}"
                exit 1
            fi
            exit 0
        else
            echo "Запуск существующего контейнера llm-container..."
            if ! docker start llm-container >/dev/null 2>&1; then
                echo -e "${RED}Ошибка при запуске контейнера. Проверьте логи: docker logs llm-container${RESET}"
                exit 1
            fi
            check_api_availability
            print_instructions
            exit 0
        fi
    else
        echo "Контейнер llm-container не найден. Требуется пересборка."
        REBUILD=1
        export REBUILD
    fi
}

# Сборка и запуск контейнера
build_and_run_container() {
    if [ "$REBUILD" -eq 1 ]; then
        if [ ! -f "Dockerfile" ]; then
            echo -e "${RED}Ошибка: Dockerfile не найден в $WORK_DIR${RESET}"
            exit 1
        fi
        echo "Сборка Docker-образа llm-api..."
        if ! docker build -t llm-api .; then
            echo -e "${RED}Ошибка при сборке Docker-образа. Проверьте логи выше.${RESET}"
            exit 1
        fi
    fi
    echo "Запуск Docker-контейнера llm-container с монтированием моделей из $WORK_DIR в /llama.cpp/models..."
    if ! docker run -d -p 5555:5555 -v "$WORK_DIR:/llama.cpp/models" --name llm-container llm-api; then
        echo -e "${RED}Ошибка при запуске контейнера. Проверьте логи: docker logs llm-container${RESET}"
        exit 1
    fi
}

# Проверка доступности API
check_api_availability() {
    sleep 2 # Даем контейнеру время на запуск
    if nc -z localhost 5555 >/dev/null 2>&1; then
        echo -e "${GREEN}API успешно запущен и доступен по адресу: http://localhost:5555${RESET}"
    else
        echo -e "${RED}Внимание: API на http://localhost:5555 недоступен. Проверьте логи: docker logs llm-container${RESET}"
    fi
}

# Вывод инструкций
print_instructions() {
    echo -e "\nДля тестирования API выполните:"
    echo "curl -X POST http://localhost:5555/generate -H 'Content-Type: application/json' -d '{\"text\": \"Привет, как дела?\"}'"
    echo "Для проверки логов: docker logs llm-container"
    echo "Для остановки контейнера: docker stop llm-container"
    echo "Для удаления контейнера: docker rm llm-container"
}

# Основной код
check_docker
setup_work_dir
parse_args "$@"
download_models
check_container
build_and_run_container
check_api_availability
print_instructions
