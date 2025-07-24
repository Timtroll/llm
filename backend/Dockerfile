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

# Создание директории для моделей
RUN mkdir -p /llama.cpp/models

# Проверка наличия моделей (опционально)
RUN echo "Проверка директории для моделей (ожидаются файлы *.gguf из volume):" && \
    ls -lh /llama.cpp/models/ || echo "Модели будут доступны после монтирования volume"

# Копирование приложения
# COPY app.py /app/
# COPY async_eav.py /app/
# COPY models.py /app/
# COPY utils.py /app/
# COPY test_async_eav.py /app/
# COPY requirements.txt /app/
# COPY controllers/ /app/
COPY . /app/

# Рабочая директория
WORKDIR /app

# Установка Python-библиотек
RUN pip3 install -r /app/requirements.txt

# Порт для FastAPI
EXPOSE 5555

# Healthcheck для мониторинга FastAPI
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:5555/api/health || exit 1

# Команда для запуска FastAPI с авторестартом
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555", "--reload"]

# Примечание: Модели (*.gguf) должны находиться в директории проекта на хосте (например, /home/troll/sites/llm).
# Монтируйте volume при запуске контейнера, например:
# docker run -d -p 5555:5555 -v /home/troll/sites/llm:/llama.cpp/models --name llm-container llm-api