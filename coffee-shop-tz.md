# Техническое задание: Coffee Shop E-Commerce API

## 1. Общее описание проекта

Разработка полнофункционального RESTful API для интернет-магазина кофейни с возможностью просмотра меню, оформления заказов, управления корзиной и административной панелью. Фронтенд реализован с использованием HTMX для динамических взаимодействий, Alpine.js для реактивности и TailwindCSS для стилизации.

## 2. Технологический стек

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0+
- **Валидация**: Pydantic 2.0+
- **База данных**: PostgreSQL 15+
- **Миграции**: Alembic
- **Аутентификация**: JWT (python-jose)
- **Хеширование паролей**: bcrypt/passlib
- **CORS**: fastapi-cors-middleware

### Frontend
- **HTML Enhancement**: HTMX (для AJAX запросов и динамического обновления DOM)
- **JavaScript Framework**: Alpine.js (для реактивности и интерактивности)
- **CSS Framework**: TailwindCSS
- **Template Engine**: Jinja2 (серверный рендеринг)
- **Build Tool**: Vite (для сборки CSS и минификации)

### Infrastructure
- **Контейнеризация**: Docker, Docker Compose
- **Reverse Proxy**: Nginx
- **Переменные окружения**: python-dotenv

## 3. Архитектура Backend (Слоистая архитектура)

```
coffee-shop-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа FastAPI
│   ├── config.py               # Конфигурация приложения
│   │
│   ├── api/                    # API Layer (Presentation)
│   │   ├── __init__.py
│   │   ├── dependencies.py     # Зависимости FastAPI
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # Главный роутер
│   │   │   └── endpoints/
│   │   │       ├── auth.py
│   │   │       ├── products.py
│   │   │       ├── categories.py
│   │   │       ├── cart.py
│   │   │       ├── orders.py
│   │   │       └── users.py
│   │
│   ├── web/                    # Web Layer (HTML endpoints)
│   │   ├── __init__.py
│   │   ├── routes.py           # HTML роуты
│   │   ├── pages/              # Page controllers
│   │   │   ├── home.py
│   │   │   ├── products.py
│   │   │   ├── cart.py
│   │   │   ├── orders.py
│   │   │   ├── auth.py
│   │   │   └── admin.py
│   │   └── htmx/               # HTMX partial endpoints
│   │       ├── cart_items.py
│   │       ├── product_list.py
│   │       └── order_status.py
│   │
│   ├── templates/              # Jinja2 Templates
│   │   ├── base.html           # Базовый шаблон
│   │   ├── components/         # Переиспользуемые компоненты
│   │   │   ├── header.html
│   │   │   ├── footer.html
│   │   │   ├── product_card.html
│   │   │   ├── cart_item.html
│   │   │   └── order_card.html
│   │   ├── pages/              # Страницы
│   │   │   ├── home.html
│   │   │   ├── products.html
│   │   │   ├── product_detail.html
│   │   │   ├── cart.html
│   │   │   ├── checkout.html
│   │   │   ├── orders.html
│   │   │   ├── profile.html
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── admin/              # Админ панель
│   │   │   ├── dashboard.html
│   │   │   ├── products.html
│   │   │   ├── orders.html
│   │   │   └── users.html
│   │   └── partials/           # HTMX partials
│   │       ├── cart_summary.html
│   │       ├── product_grid.html
│   │       └── order_list.html
│   │
│   ├── static/                 # Статические файлы
│   │   ├── css/
│   │   │   └── output.css      # Скомпилированный Tailwind
│   │   ├── js/
│   │   │   ├── alpine.js       # Alpine.js компоненты
│   │   │   └── htmx.min.js     # HTMX библиотека
│   │   └── images/
│   │
│   ├── core/                   # Core Layer
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, хеширование
│   │   ├── exceptions.py       # Кастомные исключения
│   │   └── middleware.py       # Middleware
│   │
│   ├── services/               # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── cart_service.py
│   │   ├── order_service.py
│   │   └── user_service.py
│   │
│   ├── repositories/           # Data Access Layer
│   │   ├── __init__.py
│   │   ├── base.py             # Базовый репозиторий
│   │   ├── user_repository.py
│   │   ├── product_repository.py
│   │   ├── category_repository.py
│   │   ├── cart_repository.py
│   │   └── order_repository.py
│   │
│   ├── models/                 # Database Models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── cart.py
│   │   └── order.py
│   │
│   ├── schemas/                # Pydantic Schemas (DTO)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── cart.py
│   │   ├── order.py
│   │   └── token.py
│   │
│   └── db/                     # Database
│       ├── __init__.py
│       ├── session.py          # Database session
│       └── base.py             # Base для моделей
│
├── alembic/                    # Миграции БД
│   ├── versions/
│   └── env.py
│
├── tests/                      # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   └── test_orders.py
│
├── docker/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── docker-compose.yml
│
├── tailwind.config.js          # Tailwind конфигурация
├── package.json                # npm зависимости (Tailwind, PostCSS)
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 4. Модели данных (Database Schema)

### 4.1 User (Пользователи)
```python
- id: UUID (PK)
- email: String (unique, indexed)
- username: String (unique, indexed)
- hashed_password: String
- first_name: String (nullable)
- last_name: String (nullable)
- phone: String (nullable)
- role: Enum (customer, admin)
- is_active: Boolean (default=True)
- created_at: DateTime
- updated_at: DateTime
```

### 4.2 Category (Категории напитков)
```python
- id: UUID (PK)
- name: String (unique)
- slug: String (unique, indexed)
- description: Text (nullable)
- image_url: String (nullable)
- is_active: Boolean (default=True)
- created_at: DateTime
- updated_at: DateTime
```

### 4.3 Product (Товары/Напитки)
```python
- id: UUID (PK)
- category_id: UUID (FK -> Category)
- name: String
- slug: String (unique, indexed)
- description: Text
- image_url: String (nullable)
- is_available: Boolean (default=True)
- created_at: DateTime
- updated_at: DateTime
```

### 4.4 ProductSize (Размеры товаров)
```python
- id: Integer (PK, indexed)
- product_id: UUID (FK -> Product, indexed)
- size: String(50) (nullable=False)  # small, medium, large
- price: Decimal(10, 2) (nullable=False)
- is_available: Boolean (default=True)
- created_at: DateTime (timezone=True)
- updated_at: DateTime (timezone=True)
```

### 4.5 Cart (Корзина)
```python
- id: UUID (PK)
- user_id: UUID (FK -> User, unique)
- created_at: DateTime
- updated_at: DateTime
```

### 4.6 CartItem (Элементы корзины)
```python
- id: Integer (PK)
- cart_id: UUID (FK -> Cart, indexed)
- product_size_id: Integer (FK -> ProductSize, indexed)
- quantity: Integer (nullable=False)
- price: Decimal(10, 2) (nullable=False)
- created_at: DateTime (timezone=True)
- updated_at: DateTime (timezone=True)
```

### 4.7 Order (Заказы)
```python
- id: Integer (PK, indexed)
- customer_name: String(255) (nullable=False)
- ready_time: String(10) (nullable=False)  # Время готовности заказа
- total_amount: Decimal(10, 2) (nullable=False)
- status: String(50) (nullable=False, default='pending')
- created_at: DateTime (timezone=True)
- updated_at: DateTime (timezone=True)
```

### 4.8 OrderItem (Элементы заказа)
```python
- id: Integer (PK)
- order_id: Integer (FK -> Order, indexed)
- product_size_id: Integer (FK -> ProductSize, indexed)
- quantity: Integer (nullable=False)
- price: Decimal(10, 2) (nullable=False)
- created_at: DateTime (timezone=True)
- updated_at: DateTime (timezone=True)
```

## 5. API Endpoints

### 5.1 Authentication (`/api/v1/auth`)
- `POST /register` - Регистрация нового пользователя
- `POST /login` - Вход (получение JWT токена)
- `POST /refresh` - Обновление токена
- `POST /logout` - Выход
- `GET /me` - Получение информации о текущем пользователе
- `PUT /me` - Обновление профиля

### 5.2 Categories (`/api/v1/categories`)
- `GET /` - Список всех категорий (публичный)
- `GET /{id}` - Получение категории по ID
- `POST /` - Создание категории (admin)
- `PUT /{id}` - Обновление категории (admin)
- `DELETE /{id}` - Удаление категории (admin)

### 5.3 Products (`/api/v1/products`)
- `GET /` - Список товаров с фильтрацией и пагинацией
  - Query params: `category_id`, `is_available`, `min_price`, `max_price`, `search`, `page`, `size`
- `GET /{id}` - Получение товара по ID
- `POST /` - Создание товара (admin)
- `PUT /{id}` - Обновление товара (admin)
- `DELETE /{id}` - Удаление товара (admin)
- `PATCH /{id}/availability` - Изменение доступности (admin)

### 5.4 Cart (`/api/v1/cart`)
- `GET /` - Получение корзины текущего пользователя
- `POST /items` - Добавление товара в корзину
- `PUT /items/{item_id}` - Обновление количества товара
- `DELETE /items/{item_id}` - Удаление товара из корзины
- `DELETE /` - Очистка корзины

### 5.5 Orders (`/api/v1/orders`)
- `GET /` - Список заказов пользователя
- `GET /{id}` - Получение заказа по ID
- `POST /` - Создание заказа из корзины
- `PATCH /{id}/status` - Обновление статуса заказа (admin)
- `DELETE /{id}` - Отмена заказа

### 5.6 Users (`/api/v1/users`) (Admin only)
- `GET /` - Список всех пользователей
- `GET /{id}` - Получение пользователя по ID
- `PUT /{id}` - Обновление пользователя
- `DELETE /{id}` - Удаление пользователя
- `PATCH /{id}/role` - Изменение роли пользователя

### 5.7 Admin Dashboard (`/api/v1/admin`)
- `GET /stats` - Статистика (количество заказов, выручка, популярные товары)
- `GET /orders` - Все заказы с фильтрацией

## 6. Web Routes (HTML страницы)

### 6.1 Public Pages
- `GET /` - Главная страница
- `GET /products` - Каталог товаров
- `GET /products/{slug}` - Детальная страница товара
- `GET /login` - Страница входа
- `GET /register` - Страница регистрации
- `POST /login` - Обработка входа
- `POST /register` - Обработка регистрации
- `POST /logout` - Выход

### 6.2 Protected Pages (требуют аутентификации)
- `GET /cart` - Корзина
- `GET /checkout` - Оформление заказа
- `GET /orders` - История заказов
- `GET /orders/{id}` - Детали заказа
- `GET /profile` - Профиль пользователя

### 6.3 Admin Pages (требуют роль admin)
- `GET /admin` - Админ панель (дашборд)
- `GET /admin/products` - Управление товарами
- `GET /admin/orders` - Управление заказами
- `GET /admin/users` - Управление пользователями

### 6.4 HTMX Partial Endpoints (возвращают HTML фрагменты)
- `POST /htmx/cart/add` - Добавить товар в корзину (возвращает обновленную корзину)
- `PUT /htmx/cart/items/{id}` - Обновить количество (возвращает обновленный элемент)
- `DELETE /htmx/cart/items/{id}` - Удалить из корзины (возвращает обновленную корзину)
- `GET /htmx/products` - Фильтрация товаров (возвращает список товаров)
- `GET /htmx/orders/{id}/status` - Обновление статуса заказа (возвращает статус)

## 7. HTMX и Alpine.js интеграция

### 7.1 HTMX использование
- **Добавление в корзину**: `hx-post="/htmx/cart/add"` с `hx-target="#cart-summary"` для обновления счетчика корзины
- **Фильтрация товаров**: `hx-get="/htmx/products"` с параметрами фильтрации, `hx-target="#product-grid"`
- **Обновление количества**: `hx-put="/htmx/cart/items/{id}"` с `hx-trigger="change"`
- **Удаление из корзины**: `hx-delete="/htmx/cart/items/{id}"` с `hx-swap="outerHTML"`
- **Пагинация**: `hx-get="/htmx/products?page=2"` с `hx-swap="innerHTML"`
- **Поиск**: `hx-get="/htmx/products"` с `hx-trigger="keyup changed delay:500ms"`

### 7.2 Alpine.js использование
- **Модальные окна**: `x-data="{ open: false }"` для управления состоянием
- **Выпадающие меню**: `x-show`, `x-transition` для анимаций
- **Валидация форм**: `x-data` с локальным состоянием валидации
- **Уведомления**: Toast компонент с `x-show` и автоматическим скрытием
- **Счетчик корзины**: `x-data="{ count: 0 }"` с обновлением через HTMX
- **Аккордеоны**: FAQ секции с `x-data="{ expanded: false }"`
- **Табы**: Переключение между вкладками без перезагрузки

### 7.3 Примеры интеграции

#### Добавление в корзину с HTMX
```html
<button 
  hx-post="/htmx/cart/add" 
  hx-vals='{"product_id": "{{ product.id }}", "quantity": 1}'
  hx-target="#cart-summary"
  hx-swap="innerHTML"
  class="btn btn-primary">
  Добавить в корзину
</button>
```

#### Модальное окно с Alpine.js
```html
<div x-data="{ open: false }">
  <button @click="open = true">Открыть</button>
  <div x-show="open" @click.away="open = false" class="modal">
    <!-- Содержимое модального окна -->
  </div>
</div>
```

#### Фильтрация с HTMX + Alpine.js
```html
<div x-data="{ category: '', minPrice: 0, maxPrice: 1000 }">
  <select x-model="category" 
    hx-get="/htmx/products" 
    hx-include="[name='minPrice'],[name='maxPrice']"
    hx-target="#product-grid">
    <option value="">Все категории</option>
  </select>
  <div id="product-grid">
    <!-- Товары загружаются сюда -->
  </div>
</div>
```

## 8. Функциональные требования

### 8.1 Аутентификация и авторизация
- Сессии на основе cookies (HttpOnly, Secure)
- Роли: customer, admin
- Защита страниц по ролям на уровне backend
- Хеширование паролей (bcrypt)
- CSRF защита для форм

### 8.2 Управление товарами
- CRUD операции для категорий и товаров
- Фильтрация по категориям, цене, доступности
- Поиск по названию и описанию
- Пагинация результатов

### 8.3 Корзина
- Добавление/удаление товаров через HTMX
- Изменение количества с динамическим обновлением
- Автоматический пересчет суммы
- Привязка к пользователю через сессию

### 8.4 Заказы
- Создание заказа из корзины
- Выбор типа доставки (самовывоз/доставка)
- Выбор способа оплаты
- Отслеживание статуса заказа
- История заказов

### 8.5 Административная панель
- Управление товарами и категориями
- Управление заказами (изменение статуса)
- Просмотр статистики
- Управление пользователями

## 9. Нефункциональные требования

### 9.1 Производительность
- Время ответа API < 200ms для простых запросов
- Поддержка до 1000 одновременных пользователей
- Индексы на часто запрашиваемые поля

### 9.2 Безопасность
- HTTPS обязателен в production
- CSRF защита для всех форм
- SQL injection защита (SQLAlchemy ORM)
- XSS защита (Jinja2 автоэкранирование)
- Rate limiting для API и web endpoints
- HttpOnly и Secure cookies для сессий

### 9.3 Масштабируемость
- Stateless подход (сессии в Redis или БД)
- Возможность горизонтального масштабирования
- Connection pooling для БД

### 9.4 Документация
- Автоматическая документация Swagger/OpenAPI
- README с инструкциями по запуску
- Комментарии в коде

## 10. Docker конфигурация

### 10.1 Сервисы
- **api**: FastAPI приложение (Backend + HTML рендеринг)
- **db**: PostgreSQL
- **nginx**: Reverse proxy и статический хостинг

### 10.2 Volumes
- Персистентность данных PostgreSQL
- Логи приложения
- Статические файлы (CSS, JS, изображения)

### 10.3 Networks
- Внутренняя сеть для связи сервисов

### 10.4 Nginx конфигурация
- Проксирование запросов на FastAPI backend
- Обслуживание статических файлов (CSS, JS, изображения)
- Gzip сжатие для статических ресурсов
- Кеширование статических файлов (CSS, JS, изображения)

## 11. Best Practices

### 11.1 Код
- Type hints везде
- Async/await для I/O операций
- Dependency Injection (FastAPI Depends)
- Обработка исключений на всех уровнях
- Логирование (structlog/loguru)

### 11.2 База данных
- Миграции через Alembic
- Soft delete для важных данных
- Timestamps (created_at, updated_at)
- UUID вместо auto-increment ID

### 11.3 API
- Версионирование API (/api/v1)
- Консистентные коды ответов HTTP
- Pagination для списков
- Фильтрация и сортировка
- Валидация входных данных (Pydantic)

### 11.4 Тестирование
- Unit тесты для сервисов
- Integration тесты для API
- Pytest + pytest-asyncio
- Test coverage > 80%

### 11.5 Frontend (HTMX + Alpine.js)
- Серверный рендеринг HTML через Jinja2 шаблоны
- HTMX для динамических обновлений без полной перезагрузки страницы
- Alpine.js для локальной реактивности (модальные окна, выпадающие меню, валидация форм)
- Переиспользуемые компоненты через Jinja2 макросы и includes
- TailwindCSS для utility-first стилизации
- Progressive Enhancement подход
- Responsive design (mobile-first)
- Минимальный JavaScript footprint

## 12. Переменные окружения (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/coffee_shop
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=coffee_shop

# Security
SECRET_KEY=your-secret-key-here
SESSION_SECRET_KEY=your-session-secret-key-here

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=Coffee Shop API
DEBUG=False

# Nginx
NGINX_PORT=80
```

## 13. Этапы разработки

### Этап 1: Инфраструктура (1-2 дня)
- Настройка Docker, Docker Compose
- Конфигурация PostgreSQL
- Настройка Nginx
- Базовая структура проекта Backend
- Настройка Jinja2 шаблонов

### Этап 2: Модели и миграции (2-3 дня)
- SQLAlchemy модели
- Alembic миграции
- Pydantic схемы
- Базовый репозиторий

### Этап 3: Аутентификация (2-3 дня)
- JWT токены
- Регистрация/вход
- Middleware для авторизации
- Управление ролями

### Этап 4: Основной функционал Backend (5-7 дней)
- CRUD для категорий и товаров
- Корзина
- Заказы
- Фильтрация и поиск

### Этап 5: Frontend (5-7 дней)
- Настройка Jinja2 шаблонов и структуры
- Интеграция HTMX + Alpine.js + TailwindCSS
- Базовые шаблоны: base.html, header, footer
- Страницы: Home, Products, Product Detail, Cart, Checkout, Orders, Profile
- Компоненты через Jinja2 макросы: ProductCard, CartItem, OrderCard
- HTMX endpoints для динамических обновлений (добавление в корзину, обновление количества)
- Alpine.js компоненты (модальные окна, уведомления, валидация форм)
- Аутентификация (login/register формы, сессии)
- Административная панель (управление товарами, заказами)

### Этап 6: Тестирование и оптимизация (3-4 дня)
- Написание тестов Backend
- Оптимизация запросов
- Документация
- Деплой

## 14. Дополнительные возможности (опционально)

- Загрузка изображений товаров (S3/MinIO)
- Email уведомления (SMTP)
- WebSocket для real-time обновлений заказов
- Redis для кеширования
- Celery для фоновых задач
- Prometheus + Grafana для мониторинга
- Elasticsearch для полнотекстового поиска
- Интеграция с платежными системами

## 15. Критерии приемки

### Backend
- ✅ Все API endpoints работают согласно спецификации
- ✅ Аутентификация и авторизация функционируют корректно
- ✅ CRUD операции для всех сущностей
- ✅ Корзина и заказы работают без ошибок
- ✅ Административная панель доступна для admin роли
- ✅ Документация API доступна через Swagger
- ✅ Тесты покрывают основной функционал
- ✅ Код следует PEP 8 и best practices
- ✅ Логирование настроено корректно

### Frontend
- ✅ Все страницы корректно рендерятся через Jinja2
- ✅ HTMX запросы работают без ошибок
- ✅ Alpine.js компоненты функционируют корректно
- ✅ Аутентификация работает (login/register/logout через сессии)
- ✅ Защита приватных страниц на уровне backend
- ✅ Корзина и оформление заказа функционируют
- ✅ Административная панель доступна только для admin
- ✅ Responsive design на всех устройствах
- ✅ Progressive Enhancement работает (базовый функционал без JS)

### Infrastructure
- ✅ Приложение запускается через Docker Compose одной командой
- ✅ Nginx корректно проксирует запросы и обслуживает статические файлы
- ✅ CORS настроен правильно
- ✅ Environment variables работают корректно
- ✅ Статические файлы (CSS, JS) корректно обслуживаются
