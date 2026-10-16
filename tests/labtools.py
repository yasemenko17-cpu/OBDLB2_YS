"""Спільні засоби відкритих і повних тестів: виклик функції, сценарії для сервера PostgreSQL."""
import copy
import uuid

import dbtools
import psycopg
import pytest
from conftest import load


def same(a, b):
    """Рівність; список і кортеж вважаються однаковими послідовностями."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return a == b


def checksum(text):
    """Контрольна сума міграції (така сама, як у завданнях 2 і 3)."""
    import hashlib
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return hashlib.sha256("\n".join(lines).rstrip("\n").encode("utf-8")).hexdigest()[:12]


def _fill(obj, token):
    """Підставляє {u} (унікальний токен прогону) у всі рядки структури."""
    if isinstance(obj, str):
        return obj.replace("{u}", token)
    if isinstance(obj, list):
        return [_fill(x, token) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_fill(x, token) for x in obj)
    if isinstance(obj, dict):
        return {k: _fill(v, token) for k, v in obj.items()}
    return obj


def _call(func, args, expected, label=""):
    """Викликає func(*args); expected: ValueError(текст), "db_error" або значення. Повертає результат."""
    try:
        got = func(*args)
    except psycopg.Error as exc:
        if expected == "db_error":
            return None
        pytest.fail(f"{label}сервер відхилив команду: {str(exc).splitlines()[0]}", pytrace=False)
    except ValueError as exc:
        if isinstance(expected, ValueError):
            assert str(exc) == str(expected), f"{label}текст помилки: отримано {str(exc)!r}, очікувалось {str(expected)!r}"
            return None
        pytest.fail(f"{label}неочікувана помилка ValueError: {exc}", pytrace=False)
    if isinstance(expected, ValueError):
        pytest.fail(f"{label}мала виникнути ValueError({str(expected)!r}), але функція повернула {got!r}", pytrace=False)
    if expected == "db_error":
        pytest.fail(f"{label}сервер мав відхилити команду, але вона виконалась", pytrace=False)
    return got


def run(task, fn, args, expected):
    """Чиста функція: порівнює результат; вхідні дані змінювати не можна."""
    func = getattr(load(task), fn)
    given = copy.deepcopy(args)
    if isinstance(expected, ValueError):
        with pytest.raises(ValueError) as info:
            func(*given)
        assert str(info.value) == str(expected)
    else:
        got = func(*given)
        assert same(got, expected), f"отримано {got!r}, очікувалось {expected!r}"
    assert given == args, "функція не повинна змінювати вхідні дані"


def _probe(cur, probes, token):
    problems = dbtools.run_probes(cur, _fill(probes, token))
    assert not problems, "\n".join(problems)


def run_deploy(steps):
    """Задача 1: послідовність викликів deploy_schema на одному з'єднанні."""
    func = load(1).deploy_schema
    token = uuid.uuid4().hex[:8]
    with dbtools.scratch_schema(token) as cur:
        for number, step in enumerate(_fill(steps, token), 1):
            call = step["call"]
            before = None
            cur.execute("SHOW search_path")
            before = cur.fetchone()[0]
            expected = ValueError(step["error"]) if "error" in step else ("db_error" if step.get("db_error") else step["tables"])
            got = _call(func, (cur, call["name"], call["ddl"], call.get("recreate", False)), expected, f"крок {number}: ")
            if not isinstance(expected, (ValueError, str)):
                assert same(got, expected), f"крок {number}: отримано {got!r}, очікувалось {expected!r}"
            cur.execute("SHOW search_path")
            after = cur.fetchone()[0]
            if "path" in step:
                assert after == step["path"], f"крок {number}: search_path {after!r}, очікувалось {step['path']!r}"
            if "error" in step or step.get("db_error"):
                assert after == before, f"крок {number}: після помилки search_path змінено ({before!r} -> {after!r})"
            for sql, expect in step.get("probes", []):
                problems = dbtools.run_probes(cur, [(sql, expect)])
                assert not problems, f"крок {number}: " + "\n".join(problems)


def run_migrations(steps):
    """Задача 3: послідовність викликів apply_migrations у порожній тимчасовій схемі."""
    func = load(3).apply_migrations
    with dbtools.scratch_schema() as cur:
        for number, step in enumerate(steps, 1):
            given = copy.deepcopy(step["migrations"])
            if "error" in step:
                expected = ValueError(step["error"])
            else:
                expected = "db_error" if step.get("db_error") else step["applied"]
            got = _call(func, (cur, given), expected, f"крок {number}: ")
            if not isinstance(expected, (ValueError, str)):
                assert same(got, expected), f"крок {number}: отримано {got!r}, очікувалось {expected!r}"
            assert given == step["migrations"], "функція не повинна змінювати вхідні дані"
            problems = dbtools.run_probes(cur, step.get("probes", []))
            assert not problems, f"крок {number}: " + "\n".join(problems)


def run_gen(spec, n, expected, load_into=None):
    """Задача 5: перевіряє текст CSV і, якщо задано load_into=(ddl, таблиця, запити), завантажує його сервером."""
    func = load(5).generate_csv
    given = copy.deepcopy(spec)
    got = _call(func, (given, n), expected)
    assert given == spec, "функція не повинна змінювати вхідні дані"
    if isinstance(expected, ValueError):
        return
    assert got == expected, f"отримано {got!r}, очікувалось {expected!r}"
    if load_into:
        ddl, table, probes = load_into
        with dbtools.scratch_schema() as cur:
            cur.execute(ddl)
            with cur.copy(f'COPY "{table}" FROM STDIN WITH (FORMAT csv, HEADER true)') as cp:
                cp.write(got)
            problems = dbtools.run_probes(cur, probes)
            assert not problems, "\n".join(problems)


def run_load(ddl, steps):
    """Задача 6: послідовність викликів load_csv для таблиць, створених ddl."""
    func = load(6).load_csv
    with dbtools.scratch_schema() as cur:
        cur.execute(ddl)
        for number, step in enumerate(steps, 1):
            args = (cur, step["table"], step["text"]) + ((step["delimiter"],) if "delimiter" in step else ())
            if "error" in step:
                expected = ValueError(step["error"])
            else:
                expected = "db_error" if step.get("db_error") else step["loaded"]
            got = _call(func, args, expected, f"крок {number}: ")
            if not isinstance(expected, (ValueError, str)):
                assert got == expected, f"крок {number}: отримано {got!r}, очікувалось {expected!r}"
            problems = dbtools.run_probes(cur, step.get("probes", []))
            assert not problems, f"крок {number}: " + "\n".join(problems)


def _setup(cur, ddl, setup):
    cur.execute(ddl)
    for item in setup:
        if isinstance(item, str):
            cur.execute(item)
        else:  # ("copy", таблиця, текст CSV без заголовка)
            _, table, text = item
            with cur.copy(f'COPY "{table}" FROM STDIN WITH (FORMAT csv)') as cp:
                cp.write(text)


def run_sequences(ddl, schema, setup, probes):
    """Задача 7: після завантаження з явними значеннями скрипт вирівнює послідовності."""
    func = load(7).sync_sequences_script
    given = copy.deepcopy(schema)
    with dbtools.scratch_schema() as cur:
        _setup(cur, ddl, setup)
        script = func(given)
        assert given == schema, "функція не повинна змінювати вхідні дані"
        assert isinstance(script, str), f"функція має повернути рядок, отримано {type(script).__name__}"
        if not any(c.get("identity") for t in schema["tables"].values() for c in t["columns"]):
            assert script.strip() == "", "у схемі немає стовпців identity: скрипт має бути порожнім рядком"
        if script.strip():
            try:
                cur.execute(script)
            except psycopg.Error as exc:
                pytest.fail(f"Сервер відхилив скрипт: {str(exc).splitlines()[0]}\n--- скрипт ---\n{script}", pytrace=False)
        problems = dbtools.run_probes(cur, probes)
        assert not problems, "\n".join(problems) + "\n--- скрипт ---\n" + script


def run_constraints(ddl, schema, setup, names, add_probes, validate):
    """Задача 8: іменовані обмеження NOT VALID, потім перевірка наявних даних.

    names: {ім'я: тип}; validate: "ok" або SQLSTATE помилки першого VALIDATE.
    """
    func = load(8).named_constraints_script
    given = copy.deepcopy(schema)
    with dbtools.scratch_schema() as cur:
        _setup(cur, ddl, setup)
        if isinstance(names, ValueError):
            with pytest.raises(ValueError) as info:
                func(given)
            assert str(info.value) == str(names)
            assert given == schema, "функція не повинна змінювати вхідні дані"
            return
        result = func(given)
        assert given == schema, "функція не повинна змінювати вхідні дані"
        assert isinstance(result, dict) and set(result) == {"add", "validate"}, \
            f"результат має бути словником з ключами add і validate, отримано {result!r}"
        try:
            if result["add"].strip():
                cur.execute(result["add"])
        except psycopg.Error as exc:
            pytest.fail(f"Сервер відхилив скрипт add: {str(exc).splitlines()[0]}\n--- add ---\n{result['add']}", pytrace=False)
        got = dbtools.constraints(cur)
        assert {k: v[0] for k, v in got.items()} == names, \
            f"обмеження в базі: {sorted((k, v[0]) for k, v in got.items())}, очікувалось {sorted(names.items())}"
        for name, kind in names.items():
            if kind in ("f", "c"):
                assert got[name][1] is False, f"{name} має бути додано з NOT VALID"
            else:
                assert got[name][1] is True
        problems = dbtools.run_probes(cur, add_probes)
        assert not problems, "\n".join(problems)
        if not result["validate"].strip():
            assert all(kind not in ("f", "c") for kind in names.values()), "немає команд VALIDATE для зовнішніх ключів і CHECK"
            return
        if validate == "ok":
            try:
                cur.execute(result["validate"])
            except psycopg.Error as exc:
                pytest.fail(f"Сервер відхилив скрипт validate: {str(exc).splitlines()[0]}\n--- validate ---\n{result['validate']}",
                            pytrace=False)
            assert all(v[1] for v in dbtools.constraints(cur).values()), "після VALIDATE усі обмеження мають бути перевіреними"
        else:
            with pytest.raises(psycopg.Error) as info:
                cur.execute(result["validate"])
            assert info.value.sqlstate == validate, f"код помилки {info.value.sqlstate}, очікувався {validate}"


def run_orphans(ddl, schema, setup, expected):
    """Задача 9: запити пошуку осиротілих рядків; expected: [(мітка, кількість)]."""
    func = load(9).orphan_queries
    given = copy.deepcopy(schema)
    with dbtools.scratch_schema() as cur:
        _setup(cur, ddl, setup)
        result = func(given)
        assert given == schema, "функція не повинна змінювати вхідні дані"
        assert [r[0] for r in result] == [e[0] for e in expected], \
            f"мітки: отримано {[r[0] for r in result]!r}, очікувалось {[e[0] for e in expected]!r}"
        for (label, sql), (_, count) in zip(result, expected):
            try:
                cur.execute(sql)
            except psycopg.Error as exc:
                pytest.fail(f"Запит «{label}» відхилено: {str(exc).splitlines()[0]}\n{sql}", pytrace=False)
            rows = cur.fetchall()
            assert [list(r) for r in rows] == [[count]], f"«{label}»: отримано {rows!r}, очікувалось [({count},)]\n{sql}"


def run_profile(ddl, schema, setup, expected):
    """Задача 10: профіль даних, зібраний запитами до сервера."""
    func = load(10).data_profile
    given = copy.deepcopy(schema)
    with dbtools.scratch_schema() as cur:
        _setup(cur, ddl, setup)
        got = func(cur, given)
        assert given == schema, "функція не повинна змінювати вхідні дані"
        assert same(got, expected), f"отримано {got!r}, очікувалось {expected!r}"
