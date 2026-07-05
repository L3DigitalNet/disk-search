from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_no_missing_migrations() -> None:
    # django_db IS required, despite --check --dry-run reading model/migration state
    # from disk: makemigrations also runs loader.check_consistent_history(), which
    # reads the django_migrations table, so pytest-django blocks it without the mark.
    # Fails if any model change lacks a migration (keeps schema == migrations).
    call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())
