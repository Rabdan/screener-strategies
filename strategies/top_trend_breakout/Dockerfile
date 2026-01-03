FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей (включая curl и ca-certificates для скачивания внешних пакетов)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Подавляем предупреждение о root и обновляем среду
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Скачиваем специфическую версию pandas-ta напрямую
# RUN curl -L https://www.pandas-ta.dev/assets/zip/pandas_ta-0.4.71b0.tar.gz -o pandas-ta.tar.gz

# Копируем код сервисов и стратегии
COPY services ./services
COPY strategies/top_trend_breakout/ ./
# Копируем и устанавливаем зависимости
#COPY strategies/top_trend_breakout/requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app
CMD ["python", "main.py"]
