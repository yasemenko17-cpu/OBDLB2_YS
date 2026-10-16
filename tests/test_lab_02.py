"""Відкриті тести задачі 2: План міграцій.

Запуск: pytest tests/test_lab_02.py            (усі відкриті випадки)
        pytest tests/test_lab_02.py -k S2     (лише ваш набір, наприклад другий)
Тут лише приклади з карток варіантів; повний набір перевірок є у викладача.
"""
import pytest
from labtools import run


def _ids(cases, prefix):
    return [f"{prefix}-{c[0]}-{i}" for i, c in enumerate(cases)]


# ---- Задача 2. План міграцій

T02 = [('S1',
  'migration_plan',
  ({'V001__init.sql': 'CREATE TABLE member (id integer PRIMARY KEY);\n',
    'V002__add_index.sql': 'CREATE INDEX member_id_idx ON member (id);\n',
    'V003__checks.sql': 'ALTER TABLE member ADD CONSTRAINT id_pos CHECK (id > 0);\n'},
   {}),
  ['V001__init.sql', 'V002__add_index.sql', 'V003__checks.sql']),
 ('S1',
  'migration_plan',
  ({'V001__init.sql': 'CREATE TABLE member (id integer PRIMARY KEY);\n',
    'V002__add_index.sql': 'CREATE INDEX member_id_idx ON member (id);\n',
    'V003__checks.sql': 'ALTER TABLE member ADD CONSTRAINT id_pos CHECK (id > 0);\n'},
   {1: '9e94ce257a9c', 2: '716dc81cace4'}),
  ['V003__checks.sql']),
 ('S1',
  'migration_plan',
  ({'V10__c.sql': 'c', 'V2__b.sql': 'b', 'V1__a.sql': 'a'}, {}),
  ['V1__a.sql', 'V2__b.sql', 'V10__c.sql']),
 ('S2',
  'migration_plan',
  ({'V001_init.sql': 'CREATE TABLE member (id integer PRIMARY KEY);\n'}, {}),
  ValueError("Неправильне ім'я файлу: V001_init.sql")),
 ('S2',
  'migration_plan',
  ({'V001__a.sql': 'a', 'readme.md': 'x'}, {}),
  ValueError("Неправильне ім'я файлу: readme.md")),
 ('S2',
  'migration_plan',
  ({'V001__a.sql': 'a', 'V1__b.sql': 'b'}, {}),
  ValueError('Дубльована версія 1: V001__a.sql, V1__b.sql')),
 ('S3',
  'migration_plan',
  ({'V001__init.sql': 'CREATE TABLE member (id integer PRIMARY KEY);\n',
    'V002__add_index.sql': 'CREATE INDEX member_id_idx ON member (id);\n'},
   {1: '9e94ce257a9c', 3: 'f859c9072665'}),
  ValueError('Немає файлу для застосованої версії 3')),
 ('S3',
  'migration_plan',
  ({'V001__init.sql': 'CREATE TABLE member (id integer PRIMARY KEY);\n-- правка\n'}, {1: '9e94ce257a9c'}),
  ValueError('Файл V001__init.sql змінено після застосування (версія 1)')),
 ('S3',
  'migration_plan',
  ({'V001__a.sql': 'a', 'V002__b.sql': 'b', 'V003__c.sql': 'c'}, {1: 'ca978112ca1b', 3: '2e7d2c03a950'}),
  ValueError('Міграція V002__b.sql має версію меншу за вже застосовану 3'))]


@pytest.mark.parametrize("case", T02, ids=_ids(T02, "T02"))
def test_task_02(case):
    run(2, *case[1:])
