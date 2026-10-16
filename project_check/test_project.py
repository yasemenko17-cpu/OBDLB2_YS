"""Тести частини Б: перевірка наскрізного проєкту. Запуск: pytest project_check (з кореня стартового проєкту)."""
import os
from pathlib import Path

import pytest

import check_project

PROJECT = Path(os.environ.get("PROJECT_DIR", Path(__file__).resolve().parent.parent / "project"))


@pytest.fixture(scope="module")
def deployed():
    return check_project.deploy_and_check(PROJECT)


def _assert_clean(problems):
    assert not problems, "\n" + "\n".join(problems)


def test_migrations_data_and_integrity(deployed):
    _assert_clean(deployed[1])


def test_data_dictionary(deployed):
    catalog = deployed[0]
    if catalog is None:
        pytest.fail("словник неможливо звірити зі схемою, бо міграції не виконуються", pytrace=False)
    _assert_clean(check_project.check_dictionary(PROJECT, catalog))


def test_git_history():
    _assert_clean(check_project.check_git(PROJECT))
