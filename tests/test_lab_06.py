"""Відкриті тести задачі 6: Завантаження CSV через COPY.

Запуск: pytest tests/test_lab_06.py            (усі відкриті випадки)
        pytest tests/test_lab_06.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run_load


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 6. Завантаження CSV через COPY

T06 = [('S1',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'id,name,phone,joined\n1,Оля,+380501112233,2026-01-05\n2,Іван,,2026-02-10\n',
     'loaded': 2,
     'probes': [('SELECT count(*) FROM "member"', [[2]]),
                ('SELECT phone IS NULL FROM member WHERE id = 2', [[True]]),
                ('SELECT name, joined::text FROM member WHERE id = 1', [['Оля', '2026-01-05']])]}]),
  None),
 ('S1',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'name,id\nАнна,5\n',
     'loaded': 1,
     'probes': [('SELECT id, name, phone FROM member', [[5, 'Анна', None]])]}]),
  None),
 ('S1',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'id;name\n1;Петро, молодший\n',
     'delimiter': ';',
     'loaded': 1,
     'probes': [('SELECT name FROM member', [['Петро, молодший']])]}]),
  None),
 ('S2',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member', 'text': '', 'error': 'CSV порожній'},
    {'table': 'member', 'text': '\n\n', 'error': 'CSV порожній'}]),
  None),
 ('S2',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'id,nick\n1,x\n',
     'error': 'Невідомий стовпець у CSV: nick',
     'probes': [('SELECT count(*) FROM "member"', [[0]])]}]),
  None),
 ('S2',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'nope', 'text': '', 'error': 'Немає таблиці: nope'},
    {'table': 'nope', 'text': 'id\n1\n', 'error': 'Немає таблиці: nope'}]),
  None),
 ('S3',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'id,name\n1,A\n2,B\n1,C\n',
     'db_error': True,
     'probes': [('SELECT count(*) FROM "member"', [[0]])]}]),
  None),
 ('S3',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'member',
     'text': 'id,name\n1,\n',
     'db_error': True,
     'probes': [('SELECT count(*) FROM "member"', [[0]])]},
    {'table': 'member',
     'text': 'id,name\nabc,X\n',
     'db_error': True,
     'probes': [('SELECT count(*) FROM "member"', [[0]])]},
    {'table': 'member',
     'text': 'id,name,joined\n1,A,2026-13-40\n',
     'db_error': True,
     'probes': [('SELECT count(*) FROM "member"', [[0]])]}]),
  None),
 ('S3',
  'load_csv',
  ('CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL, phone text, joined date);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note text, qty integer CHECK '
   '(qty > 0));\n'
   'CREATE TABLE "Item" ("Code" text PRIMARY KEY, "Title" text);',
   [{'table': 'order',
     'text': 'id,note,qty\n7,перша,2\n8,,3\n',
     'loaded': 2,
     'probes': [('SELECT id, note, qty FROM "order" ORDER BY id', [[7, 'перша', 2], [8, None, 3]])]},
    {'table': 'order',
     'text': 'note,qty\nнова,1\n',
     'loaded': 1,
     'probes': [('SELECT id FROM "order" WHERE note = \'нова\'', [[1]])]}]),
  None)]


@pytest.mark.parametrize("case", T06, ids=_ids(T06, "T06"))
def test_task_06(case):
    run_load(*case[2])
