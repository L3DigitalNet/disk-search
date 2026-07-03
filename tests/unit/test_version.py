"""Smoke tests for the disk_search package scaffold."""

from disk_search import __version__


def test_version__package_imported__matches_project_metadata() -> None:
    assert __version__ == "0.1.0"
