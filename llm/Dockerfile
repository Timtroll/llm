FROM ubuntu:22.04

# Установка зависимостей с очисткой кеша в одном слое
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    g++ \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка llama.cpp с фиксацией коммита
RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp && \
    cd /llama.cpp && \
    git checkout 576c82ed && \
    mkdir build && cd build && \
    cmake .. -DLLAMA_CURL=OFF && \
    make -j$(nproc)

# Установка Python-библиотек
RUN pip3 install fastapi uvicorn

# Создание директории для моделей (будет использоваться как точка монтирования volume)
RUN mkdir -p /llama.cpp/models

# Проверка наличия моделей (модели ожидаются из volume, монтируемого в /llama.cpp/models)
RUN echo "Проверка директории для моделей (ожидаются файлы *.gguf из volume):" && \
    ls -lh /llama.cpp/models/ || echo "Модели будут доступны после монтирования volume"

# Копирование приложения
COPY app.py /app/

# Рабочая директория
WORKDIR /app

# Порт для FastAPI
EXPOSE 5555

# Healthcheck для мониторинга FastAPI
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:5555/health || exit 1

# Команда для запуска FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555"]

# Примечание: Модели (*.gguf) должны находиться в директории проекта на хосте (например, /home/troll/sites/llm).
# Монтируйте volume при запуске контейнера, например:
# docker run -d -p 5555:5555 -v /home/troll/sites/llm:/llama.cpp/models --name llm-container llm-api