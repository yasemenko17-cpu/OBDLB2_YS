"""Перевірник наскрізного проєкту (частина Б, розгортання і дані): міграції, CSV, \\copy, цілісність, Git.

Запуск:  python project_check/check_project.py [тека_проєкту]   або   pytest project_check
Тека проєкту за замовчуванням: project/ (поруч із цим файлом на рівень вище). Змінна PROJECT_DIR задає іншу теку.
Потрібен PostgreSQL (змінні PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE). Перевірник працює в тимчасовій
схемі, яку видаляє. Кожне зауваження має код (MIG01, LOAD03, POST01, INT02, DICT03, GIT02 тощо) і пояснення.
"""
import hashlib
import os
import re
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
MIN_MIGRATIONS = 3
MIN_TABLES = 6
MIN_ROWS_PER_TABLE = 3
MIN_ROWS_TOTAL = 150
MIN_ROWS_BIG = 50
MIN_CHECKS = 6
MIN_COMMITS = 5
MIN_MIGRATION_COMMITS = 3
PLACEHOLDERS = {"", "—", "-", "...", "ЗАПОВНІТЬ", "TBD"}
MIGRATION_NAME = re.compile(r"V(\d+)__([a-z0-9_]+)\.sql")
COPY_LINE = re.compile(r"""^\\copy\s+(?P<table>"[^"]+"|\w+)\s*(?P<cols>\([^)]*\))?\s+from\s+'(?P<file>[^']+)'\s*(?P<rest>.*?);?\s*$""",
                       re.I)
CHECK_HEAD = re.compile(r"^--\s*check:\s*(fk|dup|null|rule)\s*:\s*(.+?)\s*$", re.I)


def _connect():
    cfg = dict(host=os.environ.get("PGHOST", "localhost"), port=int(os.environ.get("PGPORT", "5432")),
               user=os.environ.get("PGUSER", "postgres"), password=os.environ.get("PGPASSWORD", "postgres"),
               dbname=os.environ.get("PGDATABASE", "postgres"))
    conn = psycopg.connect(connect_timeout=5, **cfg)
    conn.autocommit = True
    return conn, cfg


def checksum(text):
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return hashlib.sha256("\n".join(lines).rstrip("\n").encode("utf-8")).hexdigest()[:12]


def _first_line(exc):
    return str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__


# ---------------------------------------------------------------- каталог

_COLUMNS = """
SELECT c.relname::text, a.attname::text, format_type(a.atttypid, a.atttypmod), a.attnotnull, a.attidentity::text
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace JOIN pg_attribute a ON a.attrelid = c.oid
WHERE n.nspname = current_schema() AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY c.relname, a.attnum
"""
_CONSTRAINTS = """
SELECT rel.relname::text, con.contype::text,
  (SELECT array_agg(att.attname::text ORDER BY k.ord) FROM unnest(con.conkey) WITH ORDINALITY AS k(num, ord)
     JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = k.num),
  frel.relname::text,
  (SELECT array_agg(att.attname::text ORDER BY k.ord) FROM unnest(con.confkey) WITH ORDINALITY AS k(num, ord)
     JOIN pg_attribute att ON att.attrelid = con.confrelid AND att.attnum = k.num),
  con.convalidated
FROM pg_constraint con JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace n ON n.oid = rel.relnamespace LEFT JOIN pg_class frel ON frel.oid = con.confrelid
WHERE n.nspname = current_schema() AND con.contype IN ('p', 'u', 'f', 'c')
"""


def read_catalog(cur):
    """{таблиця: {"columns": [(ім'я, тип, обов'язковий, identity)], "pk": [...], "unique": [...], "fks": [...], "checks": n}}."""
    tables = {}
    cur.execute(_COLUMNS)
    for table, col, typ, notnull, ident in cur.fetchall():
        t = tables.setdefault(table, {"columns": [], "pk": [], "unique": [], "fks": [], "checks": 0})
        t["columns"].append((col, typ, notnull, ident != ""))
    cur.execute(_CONSTRAINTS)
    for table, kind, cols, ftable, fcols, valid in cur.fetchall():
        t = tables[table]
        if kind == "p":
            t["pk"] = list(cols)
        elif kind == "u":
            t["unique"].append(list(cols))
        elif kind == "f":
            t["fks"].append({"columns": list(cols), "ref_table": ftable, "ref_columns": list(fcols), "valid": valid})
        else:
            t["checks"] += 1
    return tables


def _q(name):
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def scratch(prefix="proj"):
    """Тимчасова схема з search_path; після виходу видаляється."""
    conn, _ = _connect()
    name = f"{prefix}_{uuid.uuid4().hex[:10]}"
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
            cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
        finally:
            conn.close()


# ---------------------------------------------------------------- міграції


def list_migrations(project):
    """[(версія, ім'я файлу, текст)] за зростанням версії і зауваження за іменами."""
    folder = project / "migrations"
    if not folder.is_dir():
        return [], ["MIG00: немає теки migrations/ (файли V001__назва.sql, V002__назва.sql, ...)"]
    out, problems, seen = [], [], {}
    for path in sorted(folder.glob("*.sql")):
        m = MIGRATION_NAME.fullmatch(path.name)
        if not m:
            problems.append(f"MIG01: ім'я файлу {path.name} не відповідає шаблону V<число>__<назва>.sql (малі літери, цифри, підкреслення)")
            continue
        version = int(m.group(1))
        if version in seen:
            problems.append(f"MIG01: версія {version} повторюється у файлах {seen[version]} і {path.name}")
            continue
        seen[version] = path.name
        out.append((version, path.name, path.read_text(encoding="utf-8")))
    out.sort()
    if len(out) < MIN_MIGRATIONS:
        problems.append(f"MIG02: міграцій {len(out)}, потрібно щонайменше {MIN_MIGRATIONS} (початкова схема і ще дві зміни)")
    return out, problems


def apply_all(cur, migrations):
    """Застосовує міграції по одній у транзакції й записує їх у schema_migrations. Повертає (кількість, зауваження)."""
    cur.execute("CREATE TABLE schema_migrations (version integer PRIMARY KEY, name text NOT NULL, checksum text NOT NULL, "
                "applied_at timestamptz NOT NULL DEFAULT now())")
    done = 0
    for version, name, sql in migrations:
        cur.execute("BEGIN")
        try:
            cur.execute(sql)
            cur.execute("INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)", (version, name, checksum(sql)))
            cur.execute("COMMIT")
        except psycopg.Error as exc:
            cur.execute("ROLLBACK")
            return done, [f"MIG03: міграція {name} відхилена сервером: {_first_line(exc)}"]
        done += 1
    return done, []


def check_migrations(project, cur):
    migrations, problems = list_migrations(project)
    if not migrations:
        return None, problems
    done, errs = apply_all(cur, migrations)
    problems += errs
    if errs:
        return None, problems
    catalog = {t: v for t, v in read_catalog(cur).items() if t != "schema_migrations"}
    first = migrations[0][2]
    if len(re.findall(r"create\s+table", first, re.I)) < MIN_TABLES:
        problems.append(f"MIG04: у першій міграції {migrations[0][1]} менше {MIN_TABLES} команд CREATE TABLE "
                        "(вона має містити схему з LAB01)")
    later = " ".join(m[2] for m in migrations[1:])
    if not re.search(r"\balter\s+table\b|\bcreate\s+(unique\s+)?index\b", later, re.I):
        problems.append("MIG05: пізніші міграції не містять жодної команди ALTER TABLE або CREATE INDEX (міграція має змінювати структуру)")
    if len(catalog) < MIN_TABLES:
        problems.append(f"MIG06: після міграцій у схемі {len(catalog)} таблиць, потрібно щонайменше {MIN_TABLES}")
    for name, t in sorted(catalog.items()):
        if not t["pk"]:
            problems.append(f"MIG07: таблиця {name} не має первинного ключа")
    cur.execute("SELECT count(*) FROM schema_migrations")
    if cur.fetchone()[0] != len(migrations):
        problems.append("MIG08: журнал schema_migrations не збігається з кількістю міграцій")
    return catalog, problems


# ---------------------------------------------------------------- завантаження даних


def parse_load(project):
    """[(номер рядка, таблиця, список стовпців або None, файл, решта параметрів)] і зауваження."""
    path = project / "load.psql"
    if not path.exists():
        return [], ["LOAD00: немає файлу load.psql (команди \\copy у порядку завантаження)"]
    out, problems = [], []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("--") or line.startswith("\\set") or line.startswith("\\echo"):
            continue
        m = COPY_LINE.match(line)
        if not m:
            problems.append(f"LOAD01: load.psql, рядок {number}: очікується \\copy таблиця [(стовпці)] FROM 'файл' WITH (FORMAT csv, HEADER true)")
            continue
        table = m.group("table").strip('"')
        out.append((number, table, m.group("cols"), m.group("file"), m.group("rest") or "WITH (FORMAT csv, HEADER true)"))
    return out, problems


def run_load(project, cur, catalog):
    commands, problems = parse_load(project)
    loaded = {}
    for number, table, cols, file, rest in commands:
        if table not in catalog:
            problems.append(f"LOAD02: load.psql, рядок {number}: таблиці {table} немає у схемі")
            continue
        path = (project / file)
        if not path.is_file():
            problems.append(f"LOAD03: load.psql, рядок {number}: немає файлу {file}")
            continue
        if table in loaded:
            problems.append(f"LOAD04: таблицю {table} завантажено двічі (рядок {number})")
            continue
        sql = f"COPY {_q(table)} {cols or ''} FROM STDIN {rest}"
        try:
            with cur.copy(sql) as cp:
                cp.write(path.read_bytes())
        except psycopg.Error as exc:
            problems.append(f"LOAD05: load.psql, рядок {number}, таблиця {table}: {_first_line(exc)} "
                            "(перевірте порядок: спершу батьківські таблиці, потім дочірні; і формат CSV)")
            continue
        cur.execute(f"SELECT count(*) FROM {_q(table)}")
        loaded[table] = cur.fetchone()[0]
    for table in sorted(set(catalog) - {name for _, name, *_ in commands}):
        problems.append(f"LOAD06: таблиця {table} не завантажується: у load.psql немає команди \\copy для неї")
    for table, n in sorted(loaded.items()):
        if n < MIN_ROWS_PER_TABLE:
            problems.append(f"LOAD07: у таблиці {table} {n} рядків, потрібно щонайменше {MIN_ROWS_PER_TABLE}")
    if loaded:
        total = sum(loaded.values())
        if total < MIN_ROWS_TOTAL:
            problems.append(f"LOAD08: усього рядків {total}, потрібно щонайменше {MIN_ROWS_TOTAL}")
        if max(loaded.values()) < MIN_ROWS_BIG:
            problems.append(f"LOAD09: немає жодної таблиці з {MIN_ROWS_BIG}+ рядками (згенеруйте дані скриптом make_data.py)")
    if not (project / "make_data.py").exists():
        problems.append("LOAD10: немає скрипта make_data.py, що генерує CSV (дані мають відтворюватися)")
    return loaded, problems


def _sql_body(text):
    return re.sub(r"--[^\n]*", "", text).strip()


def check_post_load(project, cur, catalog):
    path = project / "post_load.sql"
    if not path.exists():
        return ["POST00: немає файлу post_load.sql (вирівнювання послідовностей після завантаження)"]
    text = path.read_text(encoding="utf-8")
    out = []
    if _sql_body(text):
        try:
            cur.execute(text)
        except psycopg.Error as exc:
            return [f"POST01: post_load.sql відхилено сервером: {_first_line(exc)}"]
    for table, t in sorted(catalog.items()):
        for col, _, _, identity in t["columns"]:
            if not identity:
                continue
            cur.execute(f"SELECT max({_q(col)}) FROM {_q(table)}")
            top = cur.fetchone()[0]
            cur.execute("SELECT nextval(pg_get_serial_sequence(%s, %s))", (_q(table), col))
            nxt = cur.fetchone()[0]
            if top is not None and nxt <= top:
                out.append(f"POST02: у {table}.{col} наступне значення послідовності {nxt} не більше за максимум {top} "
                           "(додайте в post_load.sql setval(...))")
    return out


# ---------------------------------------------------------------- перевірки цілісності


def parse_checks(project):
    path = project / "integrity_checks.sql"
    if not path.exists():
        return [], ["INT00: немає файлу integrity_checks.sql"]
    checks, current, problems = [], None, []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = CHECK_HEAD.match(raw.strip())
        if m:
            current = {"kind": m.group(1).lower(), "name": m.group(2), "sql": []}
            checks.append(current)
        elif current is not None:
            current["sql"].append(raw)
    for c in checks:
        c["sql"] = "\n".join(c["sql"]).strip().rstrip(";").strip()
    return checks, problems


def check_integrity(project, cur, catalog):
    checks, problems = parse_checks(project)
    if problems:
        return problems
    out = []
    if len(checks) < MIN_CHECKS:
        out.append(f"INT01: перевірок {len(checks)}, потрібно щонайменше {MIN_CHECKS} (формат: «-- check: fk: опис» і запит SELECT)")
    kinds = [c["kind"] for c in checks]
    if kinds.count("fk") < 2:
        out.append("INT02: потрібно щонайменше 2 перевірки виду fk (зовнішні ключі без батьківського рядка)")
    if kinds.count("dup") < 1:
        out.append("INT03: потрібна щонайменше 1 перевірка виду dup (дублікати за бізнес-ключем)")
    if kinds.count("rule") < 1:
        out.append("INT04: потрібна щонайменше 1 перевірка виду rule (предметне правило, якого немає в обмеженнях)")
    names = [c["name"] for c in checks]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        out.append(f"INT05: назва перевірки «{dup}» повторюється")
    for c in checks:
        label = f"{c['kind']}: {c['name']}"
        if not re.match(r"(?is)^(with|select)\b", c["sql"]):
            out.append(f"INT06: перевірка «{label}» має бути запитом SELECT (або WITH ... SELECT)")
            continue
        if not any(re.search(rf"\b{re.escape(t)}\b", c["sql"]) or re.search(rf'"{re.escape(t)}"', c["sql"]) for t in catalog):
            out.append(f"INT07: перевірка «{label}» не звертається до жодної таблиці проєкту")
            continue
        try:
            cur.execute(c["sql"])
            rows = cur.fetchall()
        except psycopg.Error as exc:
            out.append(f"INT08: перевірка «{label}» не виконується: {_first_line(exc)}")
            continue
        if rows:
            out.append(f"INT09: перевірка «{label}» знайшла порушень: {len(rows)}; перший рядок: {tuple(rows[0])!r}")
    return out


# ---------------------------------------------------------------- словник даних


def parse_dictionary(text):
    tables, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+Таблиця\s+(\S+)\s*$", line)
        if m:
            cur = tables.setdefault(m.group(1), {"desc": None, "columns": {}})
            continue
        if cur is None:
            continue
        m = re.match(r"^Опис:\s*(.*)$", line)
        if m:
            cur["desc"] = m.group(1).strip()
        if line.startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            if len(cells) < 2 or cells[0] == "Стовпець" or set(cells[0]) <= set("-: "):
                continue
            cur["columns"][cells[0]] = cells[-1]
    return tables


def check_dictionary(project, catalog):
    path = project / "data_dictionary.md"
    if not path.exists():
        return ["DICT00: немає файлу data_dictionary.md"]
    doc = parse_dictionary(path.read_text(encoding="utf-8"))
    out = []
    for name in sorted(set(catalog) - set(doc)):
        out.append(f"DICT01: таблиці {name} немає у словнику (розділ «## Таблиця {name}»)")
    for name in sorted(set(doc) - set(catalog)):
        out.append(f"DICT02: у словнику є таблиця {name}, якої немає у схемі після міграцій")
    for name in sorted(set(doc) & set(catalog)):
        db_cols = [c[0] for c in catalog[name]["columns"]]
        for c in sorted(set(db_cols) - set(doc[name]["columns"])):
            out.append(f"DICT03: у словнику таблиці {name} немає стовпця {c} (додано міграцією?)")
        for c in sorted(set(doc[name]["columns"]) - set(db_cols)):
            out.append(f"DICT04: у словнику таблиці {name} є стовпець {c}, якого немає у схемі")
        for c, desc in sorted(doc[name]["columns"].items()):
            if desc in PLACEHOLDERS:
                out.append(f"DICT06: стовпець {name}.{c} не має опису")
    return out


# ---------------------------------------------------------------- Git


def _git(project, *args):
    return subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True)


def check_git(project):
    try:
        top = _git(project, "rev-parse", "--show-toplevel")
    except FileNotFoundError:
        return ["GIT00: команда git не знайдена"]
    if top.returncode != 0:
        return ["GIT01: теку проєкту не під керуванням Git (виконайте git init, git add, git commit)"]
    out = []
    count = _git(project, "rev-list", "--count", "HEAD")
    n = int(count.stdout.strip() or 0) if count.returncode == 0 else 0
    if n < MIN_COMMITS:
        out.append(f"GIT02: комітів {n}, потрібно щонайменше {MIN_COMMITS} (схема LAB01 і окремі коміти міграцій та даних)")
    tracked = set(_git(project, "ls-files", "--", ".").stdout.split())
    for f in ("load.psql", "post_load.sql", "integrity_checks.sql", "make_data.py"):
        if f not in tracked:
            out.append(f"GIT03: файл {f} не додано в Git")
    for sub in ("migrations", "data"):
        if not any(t.startswith(sub + "/") for t in tracked):
            out.append(f"GIT03: у Git немає жодного файлу з теки {sub}/")
    log = _git(project, "log", "--format=%H", "--", "migrations")
    commits = len([x for x in log.stdout.split() if x])
    if commits < MIN_MIGRATION_COMMITS:
        out.append(f"GIT05: теку migrations/ змінено у {commits} комітах, потрібно щонайменше {MIN_MIGRATION_COMMITS} "
                   "(кожну міграцію фіксуйте окремим комітом)")
    if _git(project, "status", "--porcelain", "--", ".").stdout.strip():
        out.append("GIT04: є незафіксовані зміни у теці проєкту (git status)")
    return out


# ---------------------------------------------------------------- все разом


def deploy_and_check(project):
    """Розгортає проєкт у тимчасовій схемі й повертає (каталог, зауваження за етапами)."""
    out = []
    try:
        with scratch() as cur:
            catalog, problems = check_migrations(project, cur)
            out += problems
            if catalog is None:
                return None, out
            loaded, problems = run_load(project, cur, catalog)
            out += problems
            out += check_post_load(project, cur, catalog)
            out += check_integrity(project, cur, catalog)
            return catalog, out
    except psycopg.OperationalError as exc:
        return None, [f"MIG00: немає з'єднання з PostgreSQL ({_first_line(exc)}); запустіть сервер і задайте PGHOST, PGPORT тощо"]


def check_all(project, git=True):
    project = Path(project)
    catalog, out = deploy_and_check(project)
    if catalog is not None:
        out += check_dictionary(project, catalog)
    if git:
        out += check_git(project)
    return out


def main(argv):
    project = Path(argv[1]) if len(argv) > 1 else Path(os.environ.get("PROJECT_DIR", ROOT.parent / "project"))
    problems = check_all(project)
    for p in problems:
        print(p)
    print(f"Зауважень: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
