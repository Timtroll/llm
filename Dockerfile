FROM ubuntu:22.04

# Установка зависимостей с очисткой кеша в одном RUN
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    g++ \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка llama.cpp с явным указанием версии
# RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp && \
#     cd /llama.cpp && \
#     git checkout 576c82ed && \
#     mkdir build && cd build && \
#     cmake .. -DLLAMA_CURL=OFF && \
#     make -j$(nproc) && \
#     # Проверка наличия бинарников
#     (test -f bin/main || test -f main || { echo "Ошибка: исполняемый файл не собран"; exit 1; })
# Установка llama.cpp с фиксацией коммита
RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp && \
    cd /llama.cpp && \
    git checkout 576c82ed
WORKDIR /llama.cpp
RUN mkdir build && cd build && cmake .. -DLLAMA_CURL=OFF && make -j$(nproc)

# Установка Python-библиотек с фиксацией версий
# RUN pip3 install fastapi==0.95.2 uvicorn==0.22.0
RUN pip3 install fastapi uvicorn

# Создание структуры директорий для моделей
RUN mkdir -p /llama.cpp/models

# Копирование моделей (можно заменить на VOLUME для динамической загрузки)
COPY *.gguf /llama.cpp/models/

# Проверка моделей
RUN echo "Доступные модели:" && ls -lh /llama.cpp/models/ || echo "Модели не найдены"

# Копирование приложения
COPY app.py /app/

# Рабочая директория
WORKDIR /app

# Порт для экспоза
EXPOSE 5555

# Команда для запуска API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555"]

# FROM ubuntu:22.04

# # Установка зависимостей
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     cmake \
#     git \
#     python3 \
#     python3-pip \
#     g++ \
#     libopenblas-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Установка llama.cpp с фиксацией коммита
# RUN git clone https://github.com/ggerganov/llama.cpp.git /llama.cpp && \
#     cd /llama.cpp && \
#     git checkout 576c82ed
# WORKDIR /llama.cpp
# RUN mkdir build && cd build && cmake .. -DLLAMA_CURL=OFF && make -j$(nproc)

# # Проверка содержимого директории build
# RUN echo "Содержимое /llama.cpp/build:" && ls -l /llama.cpp/build/
# RUN echo "Содержимое /llama.cpp/build/bin (если существует):" && ls -l /llama.cpp/build/bin/ || echo "Директория /llama.cpp/build/bin/ не существует"

# # Проверка наличия исполняемого файла llama-cli или main
# RUN test -f /llama.cpp/build/bin/llama-cli && echo "Исполняемый файл llama-cli найден в /llama.cpp/build/bin/llama-cli" || \
#     test -f /llama.cpp/build/llama-cli && echo "Исполняемый файл llama-cli найден в /llama.cpp/build/llama-cli" || \
#     test -f /llama.cpp/build/bin/main && echo "Исполняемый файл main найден в /llama.cpp/build/bin/main" || \
#     test -f /llama.cpp/build/main && echo "Исполняемый файл main найден в /llama.cpp/build/main" || \
#     { echo "Ошибка: ни llama-cli, ни main не найдены в /llama.cpp/build/ или /llama.cpp/build/bin/"; exit 1; }

# # Установка Python-библиотек для API
# RUN pip3 install fastapi uvicorn

# # Копирование модели
# COPY llama-7b.Q4_0.gguf /llama.cpp/models/
# COPY model-q4_K.gguf /llama.cpp/models/

# # Копирование скрипта для API
# COPY app.py /app/

# # Рабочая директория
# WORKDIR /app

# # Команда для запуска API
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555"]

