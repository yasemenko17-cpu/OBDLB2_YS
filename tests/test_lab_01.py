"""Відкриті тести задачі 1: Розгортання схеми на сервері.

Запуск: pytest tests/test_lab_01.py            (усі відкриті випадки)
        pytest tests/test_lab_01.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run_deploy


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 1. Розгортання схеми на сервері

T01 = [('S1',
  'deploy_schema',
  ([{'call': {'name': 'shop_{u}',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'tables': ['customer', 'orders'],
     'path': 'shop_{u}',
     'probes': [("INSERT INTO customer VALUES (1, 'A')", 'ok'),
                ('INSERT INTO orders VALUES (1, 5)', 'error'),
                ('INSERT INTO orders VALUES (1, 1)', 'ok')]}],),
  None),
 ('S1',
  'deploy_schema',
  ([{'call': {'name': 'Shop',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'error': "Недопустиме ім'я схеми: Shop"},
    {'call': {'name': '1abc',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'error': "Недопустиме ім'я схеми: 1abc"},
    {'call': {'name': 'a-b',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'error': "Недопустиме ім'я схеми: a-b"},
    {'call': {'name': '',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'error': "Недопустиме ім'я схеми: "},
    {'call': {'name': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
              'ddl': 'CREATE TABLE customer (id integer PRIMARY KEY, name text NOT NULL);\n'
                     'CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customer '
                     '(id));'},
     'error': "Недопустиме ім'я схеми: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}],),
  None),
 ('S2',
  'deploy_schema',
  ([{'call': {'name': 'app_{u}', 'ddl': 'CREATE TABLE t (id integer);'},
     'tables': ['t'],
     'probes': [('INSERT INTO t VALUES (1)', 'ok')]},
    {'call': {'name': 'app_{u}', 'ddl': 'CREATE TABLE t (id integer);'},
     'error': 'Схема вже існує: app_{u}',
     'probes': [('SELECT count(*) FROM t', [[1]])]}],),
  None),
 ('S2',
  'deploy_schema',
  ([{'call': {'name': 'app_{u}', 'ddl': 'CREATE TABLE t (id integer);'},
     'tables': ['t'],
     'probes': [('INSERT INTO t VALUES (1)', 'ok')]},
    {'call': {'name': 'app_{u}',
              'ddl': 'CREATE TABLE t2 (id integer);\nCREATE TABLE t3 (id integer);',
              'recreate': True},
     'tables': ['t2', 't3'],
     'path': 'app_{u}',
     'probes': [("SELECT to_regclass('t')", [[None]]), ('SELECT count(*) FROM t2', [[0]])]}],),
  None),
 ('S3',
  'deploy_schema',
  ([{'call': {'name': 'bad_{u}', 'ddl': 'CREATE TABLE a (id integer);\nCREATE TABLE a (id integer);'},
     'db_error': True,
     'probes': [("SELECT count(*) FROM pg_namespace WHERE nspname = 'bad_{u}'", [[0]])]}],),
  None),
 ('S3',
  'deploy_schema',
  ([{'call': {'name': 'keep_{u}', 'ddl': 'CREATE TABLE t (id integer);'},
     'tables': ['t'],
     'probes': [('INSERT INTO t VALUES (1)', 'ok')]},
    {'call': {'name': 'keep_{u}', 'ddl': 'CREATE TABLE x (;', 'recreate': True},
     'db_error': True,
     'probes': [('SELECT count(*) FROM keep_{u}.t', [[1]])]}],),
  None)]


@pytest.mark.parametrize("case", T01, ids=_ids(T01, "T01"))
def test_task_01(case):
    run_deploy(*case[2])
