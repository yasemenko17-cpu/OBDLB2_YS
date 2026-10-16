"""Відкриті тести задачі 3: Застосування міграцій.

Запуск: pytest tests/test_lab_03.py            (усі відкриті випадки)
        pytest tests/test_lab_03.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run_migrations


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 3. Застосування міграцій

T03 = [('S1',
  'apply_migrations',
  ([{'migrations': [(2, 'seed', "INSERT INTO member VALUES (1, 'Оля'), (2, 'Іван');"),
                    (3, 'phone', 'ALTER TABLE member ADD COLUMN phone text;'),
                    (1, 'init', 'CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL);')],
     'applied': [1, 2, 3],
     'probes': [('SELECT count(*) FROM member', [[2]]),
                ('SELECT version, name FROM schema_migrations ORDER BY version',
                 [[1, 'init'], [2, 'seed'], [3, 'phone']]),
                ('SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() '
                 "AND table_name = 'member' ORDER BY ordinal_position",
                 [['id'], ['name'], ['phone']])]}],),
  None),
 ('S1',
  'apply_migrations',
  ([{'migrations': [(1, 'init', 'CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL);'),
                    (2, 'seed', "INSERT INTO member VALUES (1, 'Оля'), (2, 'Іван');")],
     'applied': [1, 2],
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1], [2]])]},
    {'migrations': [(1, 'init', 'CREATE TABLE member (id integer PRIMARY KEY, name text NOT NULL);'),
                    (2, 'seed', "INSERT INTO member VALUES (1, 'Оля'), (2, 'Іван');")],
     'applied': [],
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1], [2]]),
                ('SELECT count(*) FROM member', [[2]])]}],),
  None),
 ('S2',
  'apply_migrations',
  ([{'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'),
                    (2, 'b', "CREATE TABLE b (id integer);\nINSERT INTO b VALUES ('x');")],
     'db_error': True,
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1]]),
                ("SELECT count(*) FROM pg_tables WHERE schemaname = current_schema() AND tablename = 'b'",
                 [[0]]),
                ('SELECT count(*) FROM a', [[0]])]}],),
  None),
 ('S2',
  'apply_migrations',
  ([{'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'),
                    (2, 'b', "CREATE TABLE b (id integer);\nINSERT INTO b VALUES ('x');")],
     'db_error': True},
    {'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'), (2, 'b', 'CREATE TABLE b (id integer);')],
     'applied': [2],
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1], [2]]),
                ('SELECT count(*) FROM b', [[0]])]}],),
  None),
 ('S2',
  'apply_migrations',
  ([{'migrations': [(1, 'a', 'CREATE TABLE a (id integer);')], 'applied': [1]},
    {'migrations': [(1, 'a', 'CREATE TABLE a (id bigint);'), (2, 'b', 'CREATE TABLE b (id integer);')],
     'error': 'Міграцію 1 змінено після застосування',
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1]]),
                ("SELECT count(*) FROM pg_tables WHERE schemaname = current_schema() AND tablename = 'b'",
                 [[0]])]}],),
  None),
 ('S3',
  'apply_migrations',
  ([{'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'), (3, 'c', 'CREATE TABLE c (id integer);')],
     'applied': [1, 3]},
    {'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'),
                    (2, 'b', 'CREATE TABLE b (id integer);'),
                    (3, 'c', 'CREATE TABLE c (id integer);')],
     'applied': [2],
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1], [2], [3]]),
                ('SELECT count(*) FROM b', [[0]])]}],),
  None),
 ('S3',
  'apply_migrations',
  ([{'migrations': [(1, 'a', 'CREATE TABLE a (id integer);'), (2, 'b', 'CREATE TABLE b (id integer);')],
     'applied': [1, 2]},
    {'migrations': [(2, 'b', 'CREATE TABLE b (id integer);')],
     'applied': [],
     'probes': [('SELECT version FROM schema_migrations ORDER BY version', [[1], [2]])]}],),
  None)]


@pytest.mark.parametrize("case", T03, ids=_ids(T03, "T03"))
def test_task_03(case):
    run_migrations(*case[2])
