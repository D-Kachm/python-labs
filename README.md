# Car Catalog

Production-oriented, high-performance vehicle inventory and analytics management system built with Python, FastAPI, SQLAlchemy, Docker, and GitHub Actions CI/CD.

## Description

**Car Catalog** — це комплексний модульний навчально-виробничий Python-проєкт, розроблений у рамках курсу «Професійний Python» (Варіант 5: «Каталог автомобілів»). Проєкт пройшов шлях еволюційного розвитку від базового скрипта до повноцінного production-ready мікросервісу з чистою архітектурою (Clean Architecture / Domain-Driven Design), пошаровою структурою (API -> Service -> Repository -> Database), строгою типізацією, автоматизованим тестуванням (181 тест, >85% branch coverage), контейнеризацією через Docker та безперервною інтеграцією (CI/CD).

## Features

- **Предметна бізнес-логіка (Domain Model)**:
  - Сутності автомобілів (`Car`, `ElectricCar`) з інкапсуляцією, валідацією через Value Objects (`VIN`, `Money`, `Mileage`).
  - Пошук за маркою та моделлю, фільтрація за роком випуску та ціною.
  - Аналітика каталогу: середня ціна, найдорожчий автомобіль, автомобіль з мінімальним пробігом.
  - Політики знижок (Discount Policies) та патерн Специфікація/Критерії.
- **Потокова обробка та серіалізація (Streaming & Serialization)**:
  - Підтримка форматів JSON, JSONL, CSV, YAML.
  - Ленива потокова обробка (Lazy Evaluation) великих масивів даних без переповнення пам'яті.
- **Реляційна персистентність (Database & ORM)**:
  - SQLAlchemy 2.0 ORM та SQLite (підтримка SQLite/PostgreSQL через єдиний інтерфейс).
  - Зовнішні ключі з каскадним видаленням (`ON DELETE CASCADE`).
  - Міграції схеми бази даних через Alembic.
  - Репозиторний патерн (`CarRepository`, `ManufacturerRepository`).
- **Асинхронний REST API (FastAPI & Uvicorn)**:
  - CRUD-операції для виробників та автомобілів.
  - Ендпоінти аналітики та пакетної обробки.
  - Обов'язковий production healthcheck-ендпоінт (`GET /health`).
  - Інтерактивна автодокументація Swagger UI (`/docs`) та ReDoc (`/redoc`).
- **Високопродуктивні обчислення та профілювання (Performance & Optimization)**:
  - Паралельна багатопоточність (`ThreadPoolExecutor`) для I/O-bound задач.
  - Багатопроцесність (`ProcessPoolExecutor`) для CPU-bound аналітики.
  - Векторизовані розрахунки через NumPy з прискоренням до 20x.
  - Кешування аналітичних результатів через `@lru_cache` з підтримкою інвалідації.
- **Production Packaging & CI/CD**:
  - Пакетизація згідно з PEP 517 / PEP 518 / PEP 621 (`wheel`, `sdist`).
  - Управління конфігурацією через Environment Variables (`pydantic-settings`).
  - Безпека: нуль секретів у коді, `.env` виключено з Git, наявний `.env.example`.
  - Multi-stage Dockerfile з non-root користувачем (`appuser`) та вбудованим `HEALTHCHECK`.
  - Docker Compose з підтримкою persistent volumes для SQLite.
  - Автоматизований CI workflow (Ruff Lint, Ruff Format, MyPy Strict, Pytest Coverage >= 80%, Package Build, Docker Build).

## Requirements

- Python 3.11 або 3.12 (рекомендовано Python 3.12)
- Docker 24.0+ та Docker Compose v2 (для запуску в контейнері)
- Git 2.30+

## Installation

### 1. Клонування репозиторію
```bash
git clone git@github.com:D-Kachm/python-labs.git
cd python-labs
```

### 2. Створення та активація віртуального середовища
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Встановлення проєкту в режимі розробника
```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

## Configuration

Усі параметри застосунку конфігуруються через змінні оточення або локальний `.env` файл відповідно до методології Twelve-Factor App.

1. Скопіюйте шаблон змінних оточення:
```bash
cp .env.example .env
```

2. Доступні змінні конфігурації:

| Змінна | Опис | Значення за замовчуванням |
|---|---|---|
| `APP_NAME` | Назва застосунку | `Car Catalog` |
| `ENVIRONMENT` | Оточення запуску (`development`, `production`, `test`) | `development` |
| `DATABASE_URL` | SQLAlchemy URL підключення до БД | `sqlite:///cars.db` |
| `LOG_LEVEL` | Рівень деталізації логування (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `API_HOST` | Хост для прив'язки веб-сервера | `0.0.0.0` |
| `API_PORT` | Порт веб-сервера | `8000` |

> **Безпека:** Файл `.env` додано до `.gitignore`. Жодні секрети, паролі чи токени не потрапляють у репозиторій.

## Running locally

### 1. Запуск асинхронного REST API:
```bash
# Через консольний скрипт проєкту:
car-catalog --run-api --port 8000

# Або через Uvicorn напряму:
uvicorn car_catalog.api:app --reload --host 0.0.0.0 --port 8000
```
Після старту API доступне за адресою: `http://localhost:8000`.

### 2. Інтерактивне консольне меню (CLI):
```bash
car-catalog
# або
python3 -m car_catalog.main
```

### 3. Запуск експериментів з паралельності та оптимізації (Лабораторна №9):
```bash
python3 scripts/run_experiments_lab9.py
python3 benchmarks/benchmark.py
```

## Running with Docker

### 1. Збірка Docker-образу (Multi-Stage Build):
```bash
docker build -t car-catalog:1.0.0 .
```

### 2. Запуск контейнера з передачею змінних оточення:
```bash
docker run --rm -d \
  --name car-catalog-container \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=INFO \
  car-catalog:1.0.0
```

### 3. Запуск контейнера з persistent volume для бази даних:
```bash
docker run --rm -d \
  --name car-catalog-persistent \
  -p 8000:8000 \
  -v car_catalog_data:/app/data \
  -e DATABASE_URL=sqlite:////app/data/cars.db \
  -e ENVIRONMENT=production \
  car-catalog:1.0.0
```

### 4. Запуск через Docker Compose:
```bash
docker compose up -d --build
```
Для перевірки стану контейнера та healthcheck:
```bash
docker compose ps
docker compose logs -f
```

## API

| Метод | Шлях | Опис |
|---|---|---|
| `GET` | `/health` | **Production Healthcheck**: статус сервісу та поточне оточення |
| `GET` | `/` | Інформаційний ендпоінт зі статусом та версією API |
| `GET` | `/cars` | Список усіх автомобілів (фільтрація за маркою, роком, ціною) |
| `POST` | `/cars` | Створення нового автомобіля |
| `GET` | `/cars/{car_id}` | Отримання деталей конкретного автомобіля |
| `PATCH` | `/cars/{car_id}` | Часткове оновлення даних автомобіля |
| `DELETE` | `/cars/{car_id}` | Видалення автомобіля |
| `GET` | `/manufacturers` | Список виробників |
| `POST` | `/manufacturers` | Додавання нового виробника |
| `GET` | `/manufacturers/{id}/cars` | Отримання автомобілів вказаного виробника |
| `DELETE` | `/manufacturers/{id}` | Видалення виробника з каскадним видаленням авто |
| `GET` | `/manufacturers/analytics/statistics` | Агрегована статистика авто по виробниках |
| `POST` | `/external/batch-fetch` | Паралельний асинхронний збір даних через HTTPX |

### Документація API:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Testing

Проєкт містить повний набір модульних та інтеграційних тестів із перевіркою покриття гілок коду:

```bash
# Запуск усіх тестів із виведенням звіту покриття коду:
pytest -v --cov=car_catalog --cov-branch --cov-fail-under=80 --cov-report=term-missing

# Статична типізація (MyPy у строгому режимі):
mypy src tests benchmarks scripts

# Лінтинг та перевірка стилю (Ruff):
ruff check .
ruff format --check .

# Збірка дистрибутиву (wheel та sdist):
python -m build
```

## Project structure

```text
python-labs/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI/CD пайплайн
├── benchmarks/                  # Модульні бенчмарки паралельності та оптимізацій
│   ├── benchmark.py
│   ├── benchmark_numpy.py
│   ├── benchmark_processes.py
│   ├── benchmark_statistics.py
│   └── benchmark_threads.py
├── migrations/                  # Alembic міграції схеми БД
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── reports/                     # Звіти до лабораторних робіт (PDF)
│   └── Kachmar-python_lab10.pdf # Фінальний звіт ЛР №10
├── scripts/                     # Скрипти комплексних експериментів
│   ├── run_experiments_lab5.py
│   ├── run_experiments_lab6.py
│   ├── run_experiments_lab7.py
│   ├── run_experiments_lab8.py
│   └── run_experiments_lab9.py
├── src/
│   └── car_catalog/             # Основний модуль системи (src-layout)
│       ├── __init__.py          # Версія пакета (1.0.0)
│       ├── abstractions.py      # Базові абстрактні класи та політики
│       ├── analytics.py         # Аналітичні функції та NumPy векторизація
│       ├── api.py               # FastAPI REST API контролери та /health
│       ├── config.py            # Pydantic Settings та конфігурація
│       ├── criteria.py          # Патерн Specification / SearchCriteria
│       ├── database.py          # SQLAlchemy engine, session maker, init_database
│       ├── db_models.py         # ORM моделі CarEntity та Manufacturer
│       ├── dto.py               # Data Transfer Objects (Result, Optional)
│       ├── exceptions.py        # Кастомна ієрархія винятків
│       ├── exporters.py         # Експортери/імпортери (JSON, CSV, YAML)
│       ├── external_api.py      # Асинхронний HTTPX клієнт із retry та semaphore
│       ├── logging_config.py    # Налаштування логування
│       ├── main.py              # Точка входу в CLI
│       ├── models.py            # Доменні моделі (Car, ElectricCar)
│       ├── parallel.py          # ThreadPool, ProcessPool, ThreadSafeCounter
│       ├── profiling.py         # Утиліти бенчмаркінгу та профілювання
│       ├── protocols.py         # Строгі інтерфейси (typing.Protocol)
│       ├── repositories.py      # SQLAlchemy репозиторії
│       ├── schemas.py           # Pydantic схеми валідації DTO
│       ├── services.py          # Сервісний рівень бізнес-логіки
│       ├── validators.py        # Валідатори бізнес-правил
│       └── value_objects.py     # Незмінні Value Objects (VIN, Money, Mileage)
├── tests/                       # Автоматизовані тести
│   ├── conftest.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_repositories.py
│   │   └── ...
│   └── unit/
│       ├── test_production.py   # Тести Settings та /health
│       ├── test_parallel.py
│       └── ...
├── .dockerignore                # Виключення файлів для Docker build
├── .env.example                 # Приклад конфігурації оточення
├── .gitignore                   # Виключення тимчасових файлів з Git
├── Dockerfile                   # Multi-stage збірка з non-root user та healthcheck
├── docker-compose.yml           # Декларативний запуск контейнера з volume
├── LICENSE                      # MIT License
├── pyproject.toml               # Стандартизована метаінформація збірки (PEP 621)
└── README.md                    # Документація проєкту
```

## CI/CD

Проєкт використовує безперервну інтеграцію на базі **GitHub Actions** (`.github/workflows/ci.yml`). Пайплайн запускається автоматично при кожному `push` у гілки `main`, `develop` або при створенні `pull_request` та гарантує виконання таких етапів:

1. **Checkout & Setup Python**: налаштування чистого оточення Python 3.12 з кешуванням залежностей pip.
2. **Linting**: статичний аналіз коду за допомогою `ruff check .`.
3. **Format Check**: контроль стилю кодування через `ruff format --check .`.
4. **Type Check**: сувора статична типізація `mypy src tests benchmarks scripts`.
5. **Testing & Coverage**: проходження 181 тесту з перевіркою мінімального порогу покриття гілок коду `pytest --cov-fail-under=80`.
6. **Package Build**: верифікація створення бінарного `wheel` та `sdist` через `python -m build`.
7. **Docker Build**: перевірка побудови контейнера `docker build -t car-catalog:ci .`.

Лише за умови успішного проходження всіх 7 етапів (Green Pipeline) коміт вважається валідним для продакшн-релізу.

## Authors

- **Денис Качмар** — студент групи ФЕП-33с факультету електроніки та комп'ютерних технологій Львівського національного університету імені Івана Франка.
- Email: `Denys.Kachmar@lnu.edu.ua`
- GitHub: [D-Kachm](https://github.com/D-Kachm)
