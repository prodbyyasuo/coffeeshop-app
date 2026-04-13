# Coffee Shop E-Commerce API

Полнофункциональное веб-приложение для интернет-магазина кофейни с использованием FastAPI, HTMX, Alpine.js и TailwindCSS.

## Технологический стек

### Backend
- FastAPI (Python 3.11+)
- SQLAlchemy 2.0+ (ORM)
- PostgreSQL 15+
- Alembic (миграции)
- Pydantic 2.0+ (валидация)

### Frontend
- HTMX (динамические обновления)
- Alpine.js (реактивность)
- TailwindCSS (стилизация)
- Jinja2 (шаблоны)

### Infrastructure
- Docker & Docker Compose
- Nginx (reverse proxy)

## Быстрый старт

### Предварительные требования
- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

### Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd coffeeshop-app
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Запустите приложение через Docker Compose:
```bash
cd docker
docker-compose up -d
```

4. Приложение будет доступно по адресу:
- Frontend: http://localhost
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Локальная разработка (без Docker)

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите PostgreSQL (или используйте Docker для БД)

4. Примените миграции:
```bash
alembic upgrade head
```

5. Запустите сервер разработки:
```bash
uvicorn app.main:app --reload
```

## Структура проекта

```
coffeeshop-app/
├── app/                    # Основное приложение
│   ├── api/               # API endpoints
│   ├── web/               # Web routes (HTML)
│   ├── templates/         # Jinja2 шаблоны
│   ├── static/            # Статические файлы
│   ├── models/            # SQLAlchemy модели
│   ├── schemas/           # Pydantic схемы
│   ├── services/          # Бизнес-логика
│   ├── repositories/      # Работа с БД
│   ├── core/              # Ядро (security, exceptions)
│   └── db/                # Database конфигурация
├── alembic/               # Миграции БД
├── docker/                # Docker конфигурация
├── tests/                 # Тесты
└── requirements.txt       # Python зависимости
```

## Основные функции

- ✅ Просмотр каталога товаров
- ✅ Корзина покупок
- ✅ Оформление заказов
- ✅ Аутентификация пользователей
- ✅ Административная панель
- ✅ Управление товарами и категориями
- ✅ История заказов

## API Документация

После запуска приложения документация API доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Разработка

### Создание миграций

```bash
alembic revision --autogenerate -m "описание изменений"
alembic upgrade head
```

### Запуск тестов

```bash
pytest
```

## Лицензия

MIT
