# Python Labs

Навчальний проєкт з дисципліни «Професійний Python». 
Містить каталог автомобілів (Варіант 5), який розвивається протягом курсу.

## Author
Студент: Качмар Денис Богданович
Група: ФЕП-33с

## Requirements
Python 3.11+

## Installation & Run
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .

# Запуск інтерактивного консольного меню:
car-catalog

# Запуск повної автоматичної демонстрації функціоналу (Лаб 2):
python3 -m car_catalog.main --demo

# Запуск експериментального бенчмарку (1k, 10k, 100k):
python3 -m car_catalog.main --benchmark
```
