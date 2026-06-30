"""Tests for frozen/desktop path helpers."""

from pathlib import Path

from open_notebook.utils.frozen import is_frozen, migration_path, project_root, resource_path


def test_is_frozen_false_in_dev():
    assert is_frozen() is False


def test_project_root_is_repo_root():
    root = project_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "open_notebook").is_dir()


def test_resource_path_resolves_migration():
    path = Path(migration_path("1.surrealql"))
    assert path.is_file()
    assert path.name == "1.surrealql"


def test_migration_path_under_migrations_dir():
    assert resource_path("open_notebook/database/migrations/15.surrealql").is_file()
