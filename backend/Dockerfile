FROM ubuntu:22.04

# Установка зависимостей + Vulkan
RUN apt update && \
    apt install -y \
        curl \
        build-essential \
        cmake \
        git \
        python3 \
        python3-pip \
        g++ \
        libopenblas-dev \
        ninja-build \
        software-properties-common \
        wget \
    && add-apt-repository universe \
    && apt update \
    && apt-get install -y \
        vulkan-tools \
        mesa-vulkan-drivers \
        libvulkan-dev \
        libvulkan1 \
        vulkan-validationlayers \
    && rm -rf /var/lib/apt/lists/*

# Установка llama.cpp с поддержкой VULKAN
RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp && \
    cd /llama.cpp && \
    git checkout 576c82ed && \
    mkdir build && cd build && \
    cmake .. -DLLAMA_VULKAN=ON -DLLAMA_CURL=OFF && \
    make -j$(nproc)

# Проверка: доступен ли GPU (для отладки, можно убрать в продакшене)
RUN echo "=== Проверка Vulkan ===" && \
    vulkaninfo | grep "GPU id" || echo "Vulkan установлен, но GPU не найден (нормально в билде)"

# Директория для моделей
RUN mkdir -p /llama.cpp/models

# Проверка наличия моделей (опционально)
RUN echo "Проверка директории для моделей (ожидаются файлы *.gguf из volume):" && \
    ls -lh /llama.cpp/models/ || echo "Модели будут доступны после монтирования volume"

# Копирование приложения
COPY . /app/
WORKDIR /app

# Установка Python-зависимостей
RUN pip3 install -r requirements.txt

# Порт
EXPOSE 5555

# Healthcheck для мониторинга FastAPI
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:5555/api/health || exit 1

# Команда для запуска FastAPI с авторестартом
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555", "--reload"]

# Примечание: Модели (*.gguf) должны находиться в директории проекта на хосте (например, /home/troll/sites/llm).
# Монтируйте volume при запуске контейнера, например:
# docker run -d -p 5555:5555 -v /home/troll/sites/llm:/llama.cpp/models --name llm-container llm-api