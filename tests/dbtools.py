"""Робота з PostgreSQL у тестах: з'єднання, тимчасова схема, перевірні запити.

Параметри з'єднання беруться зі змінних середовища PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
(у Codespaces вони вже задані). Типові значення: localhost, 5432, postgres, postgres, postgres.
"""
import os
import uuid
from contextlib import contextmanager

import psycopg
import pytest


def _settings():
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "postgres"),
        "dbname": os.environ.get("PGDATABASE", "postgres"),
    }


def connect():
    cfg = _settings()
    try:
        conn = psycopg.connect(connect_timeout=5, **cfg)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"Немає з'єднання з PostgreSQL ({cfg['host']}:{cfg['port']}): {exc}\n"
            "Запустіть сервер: у Codespaces він стартує разом із середовищем; локально виконайте\n"
            "  docker run --name lab-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:18\n"
            "і за потреби задайте PGHOST, PGPORT, PGUSER, PGPASSWORD.",
            pytrace=False)
    conn.autocommit = True
    return conn


@contextmanager
def scratch_schema(token=None):
    """Створює порожню схему lab02_<токен>, ставить її в search_path і видаляє після використання."""
    conn = connect()
    token = token or uuid.uuid4().hex[:10]
    name = "lab02_" + token
    cur = conn.cursor()
    try:
        cur.execute(f'CREATE SCHEMA "{name}"')
        cur.execute(f'SET search_path = "{name}"')
        yield cur
    finally:
        try:
            cur.execute("ROLLBACK")
        except Exception:  # noqa: BLE001
            pass
        try:
            cur.execute("SET search_path = public")
            cur.execute("SELECT nspname FROM pg_namespace WHERE nspname = %s OR nspname LIKE %s",
                        (name, "%\\_" + token))
            for (found,) in cur.fetchall():
                cur.execute('DROP SCHEMA IF EXISTS "' + found + '" CASCADE')
        finally:
            conn.close()


def run_probes(cur, probes):
    """Виконує перевірні запити. Очікування: "ok", "error" або список рядків результату SELECT."""
    problems = []
    for number, (sql, expect) in enumerate(probes, 1):
        try:
            cur.execute(sql)
            rows = cur.fetchall() if cur.description else None
            failed = False
        except psycopg.Error as exc:
            rows, failed, err = None, True, str(exc).splitlines()[0]
        if expect == "ok":
            if failed:
                problems.append(f"запит {number} мав виконатися, але сервер відхилив: {sql} -> {err}")
        elif expect == "error":
            if not failed:
                problems.append(f"запит {number} мав бути відхилений сервером, але виконався: {sql}")
        else:
            if failed:
                problems.append(f"запит {number} не виконався: {sql} -> {err}")
            elif [list(r) for r in rows] != expect:
                problems.append(f"запит {number}: {sql} -> отримано {[list(r) for r in rows]!r}, очікувалось {expect!r}")
    return problems


def constraints(cur):
    """{ім'я обмеження: (тип p/u/f/c, перевірене?)} у поточній схемі."""
    cur.execute("SELECT con.conname::text, con.contype::text, con.convalidated "
                "FROM pg_constraint con JOIN pg_namespace n ON n.oid = con.connamespace "
                "WHERE n.nspname = current_schema() AND con.contype IN ('p', 'u', 'f', 'c')")
    return {name: (kind, valid) for name, kind, valid in cur.fetchall()}
