"""Відкриті тести задачі 7: Вирівнювання послідовностей.

Запуск: pytest tests/test_lab_07.py            (усі відкриті випадки)
        pytest tests/test_lab_07.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run_sequences


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 7. Вирівнювання послідовностей

T07 = [('S1',
  'sync_sequences_script',
  ('CREATE TABLE member (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name text);',
   {'tables': {'member': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True},
                                      {'name': 'name', 'type': 'text', 'nullable': True}],
                          'pk': ['id'],
                          'unique': [],
                          'fks': [],
                          'checks': []}}},
   [('copy', 'member', '5,A\n9,B\n')],
   [("INSERT INTO member (name) VALUES ('C') RETURNING id", [[10]]),
    ("INSERT INTO member (name) VALUES ('C') RETURNING id", [[11]])]),
  None),
 ('S1',
  'sync_sequences_script',
  ('CREATE TABLE member (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name text);',
   {'tables': {'member': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True},
                                      {'name': 'name', 'type': 'text', 'nullable': True}],
                          'pk': ['id'],
                          'unique': [],
                          'fks': [],
                          'checks': []}}},
   [],
   [("INSERT INTO member (name) VALUES ('C') RETURNING id", [[1]]),
    ("INSERT INTO member (name) VALUES ('C') RETURNING id", [[2]])]),
  None),
 ('S2',
  'sync_sequences_script',
  ('CREATE TABLE member (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name text);\n'
   'CREATE TABLE "order" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, member_id integer);\n'
   'CREATE TABLE plan (code text PRIMARY KEY);',
   {'tables': {'member': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True},
                                      {'name': 'name', 'type': 'text', 'nullable': True}],
                          'pk': ['id'],
                          'unique': [],
                          'fks': [],
                          'checks': []},
               'order': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True},
                                     {'name': 'member_id', 'type': 'integer', 'nullable': True}],
                         'pk': ['id'],
                         'unique': [],
                         'fks': [],
                         'checks': []},
               'plan': {'columns': [{'name': 'code', 'type': 'text', 'nullable': False}],
                        'pk': ['code'],
                        'unique': [],
                        'fks': [],
                        'checks': []}}},
   [('copy', 'member', '1,A\n2,B\n3,C\n'),
    'INSERT INTO "order" (id, member_id) OVERRIDING SYSTEM VALUE VALUES (41, 1)',
    "INSERT INTO plan VALUES ('basic')"],
   [('INSERT INTO "order" (member_id) VALUES (2) RETURNING id', [[42]]),
    ("INSERT INTO member (name) VALUES ('C') RETURNING id", [[4]]),
    ('SELECT count(*) FROM plan', [[1]])]),
  None),
 ('S2',
  'sync_sequences_script',
  ('CREATE TABLE a (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY);\n'
   'CREATE TABLE b (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY);',
   {'tables': {'a': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True}],
                     'pk': ['id'],
                     'unique': [],
                     'fks': [],
                     'checks': []},
               'b': {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True}],
                     'pk': ['id'],
                     'unique': [],
                     'fks': [],
                     'checks': []}}},
   ['INSERT INTO a (id) OVERRIDING SYSTEM VALUE VALUES (100), (200)'],
   [('INSERT INTO a DEFAULT VALUES RETURNING id', [[201]]),
    ('INSERT INTO b DEFAULT VALUES RETURNING id', [[1]])]),
  None),
 ('S3',
  'sync_sequences_script',
  ('CREATE TABLE "Item" ("Id" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "Title" text);',
   {'tables': {'Item': {'columns': [{'name': 'Id', 'type': 'integer', 'nullable': False, 'identity': True},
                                    {'name': 'Title', 'type': 'text', 'nullable': True}],
                        'pk': ['Id'],
                        'unique': [],
                        'fks': [],
                        'checks': []}}},
   [('copy', 'Item', '100,A\n250,B\n')],
   [('INSERT INTO "Item" ("Title") VALUES (\'C\') RETURNING "Id"', [[251]])]),
  None),
 ('S3',
  'sync_sequences_script',
  ('CREATE TABLE "it\'s" (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY);',
   {'tables': {"it's": {'columns': [{'name': 'id', 'type': 'integer', 'nullable': False, 'identity': True}],
                        'pk': ['id'],
                        'unique': [],
                        'fks': [],
                        'checks': []}}},
   ['INSERT INTO "it\'s" (id) OVERRIDING SYSTEM VALUE VALUES (7)'],
   [('INSERT INTO "it\'s" DEFAULT VALUES RETURNING id', [[8]])]),
  None)]


@pytest.mark.parametrize("case", T07, ids=_ids(T07, "T07"))
def test_task_07(case):
    run_sequences(*case[2])
