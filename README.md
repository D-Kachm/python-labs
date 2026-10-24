# Python Labs

Навчальний проєкт з дисципліни «Професійний Python». 
Містить каталог автомобілів (Варіант 5), який розвивається протягом курсу.

## Author
Студент: Качмар Денис Богданович  
Група: ФЕП-33с  

## Requirements
Python 3.11+

## Installation & Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

## Running the Application

### 1. Інтерактивне консольне меню:
```bash
car-catalog
# або
python3 -m car_catalog.main
```

### 2. Лабораторна робота №3 (Потоковий конвеєр, ітератори та генератори):
```bash
# Демонстрація повного streaming pipeline (читання, валідація, фільтрація, batching, itertools):
python3 -m car_catalog.main --stream-demo

# Експериментальне порівняння Eager vs Lazy (час, RAM, TTFR, early termination на 10k, 100k, 500k):
python3 -m car_catalog.main --stream-benchmark

# Генерація довільного набору даних (наприклад, 100 000 записів):
python3 -m car_catalog.main --generate-dataset 100000
```

### 3. Лабораторна робота №2 (Структури даних та декомпозиція):
```bash
# Автоматична демонстрація функціоналу Лаб 2:
python3 -m car_catalog.main --demo

# Експериментальний бенчмарк пошуку (list vs dict index):
python3 -m car_catalog.main --benchmark
```

## Running Tests
```bash
python3 -m unittest discover tests/ -v
```
