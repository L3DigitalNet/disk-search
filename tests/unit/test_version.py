"""Smoke tests for the hw_radar package scaffold."""

from hw_radar import __version__


def test_version__package_imported__matches_project_metadata() -> None:
    assert __version__ == "0.1.0"
