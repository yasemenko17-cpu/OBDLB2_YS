"""Генерує CSV-файли теки data/ детермінованим способом: повторний запуск дає ті самі файли.

Запуск (з теки project):  python make_data.py
Генератор випадкових чисел створюйте з фіксованим зерном: random.Random(42).
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data"
rnd = random.Random(42)


def write(name, header, rows):
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    # Приклад: довідник на 3 рядки. Додайте свої таблиці й зв'язки; порожнє значення в CSV означає NULL.
    write("example", ["id", "title"], [(i, f"Елемент {i}") for i in range(1, 4)])


if __name__ == "__main__":
    main()
