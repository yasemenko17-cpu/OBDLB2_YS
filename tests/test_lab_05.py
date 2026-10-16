"""Відкриті тести задачі 5: Генерація тестових даних у CSV.

Запуск: pytest tests/test_lab_05.py            (усі відкриті випадки)
        pytest tests/test_lab_05.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run_gen


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 5. Генерація тестових даних у CSV

T05 = [('S1', 'generate_csv', ([{'name': 'id', 'kind': 'seq'}], 3, 'id\n1\n2\n3\n'), None),
 ('S1',
  'generate_csv',
  ([{'name': 'id', 'kind': 'seq', 'start': 100, 'step': 10},
    {'name': 'city', 'kind': 'cycle', 'values': ['Львів', 'Київ']}],
   3,
   'id,city\n100,Львів\n110,Київ\n120,Львів\n'),
  None),
 ('S1',
  'generate_csv',
  ([{'name': 'email', 'kind': 'template', 'pattern': 'user{i:03d}@example.com'}],
   2,
   'email\nuser001@example.com\nuser002@example.com\n'),
  None),
 ('S2',
  'generate_csv',
  ([{'name': 'd', 'kind': 'date', 'start': '2026-01-30'}],
   4,
   'd\n2026-01-30\n2026-01-31\n2026-02-01\n2026-02-02\n'),
  None),
 ('S2',
  'generate_csv',
  ([{'name': 'd', 'kind': 'date', 'start': '2026-02-25', 'step_days': 7}],
   3,
   'd\n2026-02-25\n2026-03-04\n2026-03-11\n'),
  None),
 ('S2',
  'generate_csv',
  ([{'name': 'price', 'kind': 'decimal', 'start': '10', 'step': '2.5'}], 3, 'price\n10.00\n12.50\n15.00\n'),
  None),
 ('S2',
  'generate_csv',
  ([{'name': 'id', 'kind': 'seq'},
    {'name': 'phone', 'kind': 'template', 'pattern': '+380{i:09d}', 'null_every': 2}],
   4,
   'id,phone\n1,+380000000001\n2,\n3,+380000000003\n4,\n'),
  None),
 ('S3', 'generate_csv', ([{'name': 'id', 'kind': 'seq'}], -1, ValueError("n не може бути від'ємним")), None),
 ('S3', 'generate_csv', ([], 3, ValueError('Порожній опис стовпців')), None),
 ('S3',
  'generate_csv',
  ([{'name': 'id', 'kind': 'seq'}, {'name': 'x', 'kind': 'random'}],
   1,
   ValueError('Невідомий вид генератора: random')),
  None),
 ('S3',
  'generate_csv',
  ([{'name': 'id', 'kind': 'seq'},
    {'name': 'full_name', 'kind': 'template', 'pattern': 'Клієнт {i}'},
    {'name': 'email', 'kind': 'template', 'pattern': 'c{i}@example.com'},
    {'name': 'city', 'kind': 'cycle', 'values': ['Київ', 'Львів', 'Одеса']},
    {'name': 'joined', 'kind': 'date', 'start': '2026-03-01', 'step_days': 2},
    {'name': 'balance', 'kind': 'decimal', 'start': '100', 'step': '25.5'}],
   6,
   'id,full_name,email,city,joined,balance\n'
   '1,Клієнт 1,c1@example.com,Київ,2026-03-01,100.00\n'
   '2,Клієнт 2,c2@example.com,Львів,2026-03-03,125.50\n'
   '3,Клієнт 3,c3@example.com,Одеса,2026-03-05,151.00\n'
   '4,Клієнт 4,c4@example.com,Київ,2026-03-07,176.50\n'
   '5,Клієнт 5,c5@example.com,Львів,2026-03-09,202.00\n'
   '6,Клієнт 6,c6@example.com,Одеса,2026-03-11,227.50\n',
   ('CREATE TABLE customer (id integer PRIMARY KEY, full_name text NOT NULL, email text UNIQUE, city text, '
    'joined date, balance numeric(12,2));',
    'customer',
    [('SELECT count(*) FROM customer', [[6]]),
     ('SELECT city, count(*) FROM customer GROUP BY city ORDER BY city',
      [['Київ', 2], ['Львів', 2], ['Одеса', 2]]),
     ('SELECT joined::text, balance::text FROM customer WHERE id = 6', [['2026-03-11', '227.50']]),
     ('SELECT sum(balance)::text FROM customer', [['982.50']])])),
  None)]


@pytest.mark.parametrize("case", T05, ids=_ids(T05, "T05"))
def test_task_05(case):
    run_gen(*case[2])
