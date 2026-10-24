# Python Labs

Навчальний проєкт з дисципліни «Професійний Python». 
Містить каталог автомобілів (Варіант 5), який модульно розвивається протягом 10 лабораторних робіт.

## Author
Студент: Качмар Денис Богданович  
Група: ФЕП-33с  

## Requirements
Python 3.11+ (рекомендовано 3.12)

## Installation & Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Running the Application

### 1. Інтерактивне консольне меню:
```bash
car-catalog
# або
python3 -m car_catalog.main
```

### 2. Лабораторна робота №8 (Мережеве та асинхронне програмування. REST API):
```bash
# Запуск асинхронного REST API сервера (FastAPI + Uvicorn):
car-catalog --run-api
# або з кастомним портом:
python3 -m car_catalog.main --run-api --port 8000
# або напряму через uvicorn:
uvicorn car_catalog.api:app --reload --port 8000

# Інтерактивна документація Swagger UI:
# http://127.0.0.1:8000/docs
# ReDoc:
# http://127.0.0.1:8000/redoc

# Запуск автоматизованих тестів REST API (21 інтеграційний тест):
pytest tests/integration/test_api.py -v

# Демонстрація 7 ключових асинхронних експериментів (FastAPI CRUD, Pydantic валідація, Query параметри, Async Task/gather прискорення, Semaphore rate limiting, HTTPX retry/timeout, Batch агрегація):
python3 scripts/run_experiments_lab8.py
```

### 3. Лабораторна робота №7 (Робота з базами даних у Python):
```bash
# Запуск міграцій схеми бази даних за допомогою Alembic:
alembic current
alembic upgrade head
alembic downgrade -1

# Запуск автоматизованих інтеграційних тестів репозиторіїв та ORM:
pytest tests/integration/test_repositories.py -v

# Демонстрація 7 ключових persistence-експериментів (CRUD, ON DELETE CASCADE, DB-API, ACID, GROUP BY, UNIQUE VIN, Alembic):
python3 scripts/run_experiments_lab7.py
```

### 4. Лабораторна робота №6 (Автоматизоване тестування Python-програм):
```bash
# Запуск повного тестового набору з покриттям коду та перевіркою розгалужень (Branch Coverage):
pytest -v --cov=car_catalog --cov-branch --cov-report=term-missing --cov-report=html

# Запуск тільки модульних тестів (Unit Tests):
pytest tests/unit/ -v

# Запуск тільки інтеграційних тестів (Integration Tests):
pytest tests/integration/ -v

# Запуск 7 експериментів лабораторної роботи №6:
python3 scripts/run_experiments_lab6.py
```

### 5. Лабораторна робота №5 (Обробка помилок, файли та серіалізація):
```bash
# Демонстрація надійного імпорту/експорту (fail-fast, tolerant mode, atomic replace, exception chaining):
python3 -m car_catalog.main --reliable-demo
# Запуск конвеєра за конфігураційним файлом:
python3 -m car_catalog.main --reliable-pipeline config.yaml
# Запуск автоматизованих експериментів 1-5 Лабораторної №5:
python3 scripts/run_experiments_lab5.py
```

### 6. Лабораторна робота №4 (Професійне ООП та система типів Python):
```bash
# Демонстрація ООП, протоколів, DI, Value Objects та Generic Repository:
python3 -m car_catalog.main --oop-demo

# Статична перевірка типів через mypy у строгому режимі:
mypy src tests scripts
```

### 7. Лабораторна робота №3 (Потоковий конвеєр, ітератори та генератори):
```bash
# Демонстрація повного streaming pipeline (читання, валідація, фільтрація, batching, itertools):
python3 -m car_catalog.main --stream-demo

# Експериментальне порівняння Eager vs Lazy (час, RAM, TTFR, early termination на 10k, 100k, 500k):
python3 -m car_catalog.main --stream-benchmark

# Генерація довільного набору даних (наприклад, 100 000 записів):
python3 -m car_catalog.main --generate-dataset 100000
```

### 8. Лабораторна робота №2 (Структури даних та декомпозиція):
```bash
# Автоматична демонстрація функціоналу Лаб 2:
python3 -m car_catalog.main --demo

# Експериментальний бенчмарк пошуку (list vs dict index):
python3 -m car_catalog.main --benchmark
```

## Running Tests
```bash
# Рекомендована команда запуску pytest із формуванням coverage звіту:
pytest -v --cov=car_catalog --cov-branch --cov-report=term-missing
```

## Static Type Checking
```bash
mypy src tests scripts
```
