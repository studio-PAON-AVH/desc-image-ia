# tests/test_settings.py
import os
import pytest
from backend.core.settings import _env_file


def test_env_file_uses_app_env_variable(monkeypatch, tmp_path):
    """APP_ENV contrôle le chemin retourné par _env_file()."""
    custom_path = str(tmp_path / ".env.custom")
    monkeypatch.setenv("APP_ENV", custom_path)
    assert _env_file() == custom_path


def test_env_file_returns_dotenv_when_app_env_is_dev(monkeypatch):
    """APP_ENV=.env.dev → _env_file() retourne '.env.dev'."""
    monkeypatch.setenv("APP_ENV", ".env.dev")
    assert _env_file() == ".env.dev"


def test_settings_env_file_default_when_no_app_env(monkeypatch):
    """Sans APP_ENV, _env_file() retourne '.env'."""
    monkeypatch.delenv("APP_ENV", raising=False)
    assert _env_file() == ".env"
