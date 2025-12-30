# Crypto Screener & Strategies

Проект для скрининга криптовалют и запуска торговых стратегий с визуализацией на графиках.

## Архитектура
- **Redis**: Используется как брокер сообщений (Pub/Sub) и хранилище временных данных (свечи, текущие состояния).
- **API (FastAPI)**: Предоставляет REST эндпоинты для фронтенда и управляет WebSocket соединениями для передачи данных в реальном времени.
- **Aggregate Service**: Обрабатывает входящие потоки данных и агрегирует их для хранения и отображения.
- **Web (Svelte/Vite)**: Пользовательский интерфейс с интерактивными графиками (Lightweight Charts).

## Быстрый запуск через Docker

Самый простой способ запустить все службы — использовать Docker Compose:

```bash
docker-compose up --build
```

После запуска:
- Фронтенд: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000](http://localhost:8000)
- Документация API (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

## Запуск для разработки (Manual)

### 1. Инфраструктура
Для работы необходим запущенный Redis. Можно запустить только его через Docker:
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

### 2. Backend (API и Aggregate)
Перейдите в корень проекта, установите зависимости и запустите службы:

```bash
# Установка зависимостей
pip install -r services/requirements.txt

# Запуск API
python services/api.py

# Запуск Aggregate (в другом терминале)
python services/aggregate.py
```

### 3. Frontend (Web)
Перейдите в директорию `web`, установите зависимости и запустите dev-сервер:

```bash
cd web
npm install
npm run dev
```

## Переменные окружения (Environment Variables)

В `docker-compose.yml` и коде используются следующие переменные:
- `REDIS_HOST`: Адрес хоста Redis (по умолчанию `localhost` или `redis` в Docker).
- `DB_PATH`: Путь к файлу базы данных SQLite для хранения сделок.
- `VITE_API_URL`: URL API сервера для фронтенда.
- `VITE_WS_URL`: URL WebSocket сервера для фронтенда.

## Структура проекта
- `services/`: Код бэкенда (API, агрегация, хранилище).
- `strategies/`: Код торговых стратегий.
- `web/`: Фронтенд на Svelte 5.
- `data/`: Локальное хранилище для SQLite и логов (создается автоматически).
