FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Создаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 5000 7860

# Команда по умолчанию
CMD ["python", "app/api.py"]