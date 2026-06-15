# tests/test_auth_schemas.py
import pytest
from pydantic import ValidationError


def test_user_create_username_too_short():
    from backend.auth.schemas import UserCreate

    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="ab", email="test@example.com", password="secret123")
    assert "3 caractères" in str(exc_info.value)


def test_user_create_password_too_short():
    from backend.auth.schemas import UserCreate

    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="alice", email="test@example.com", password="short")
    assert "8 caractères" in str(exc_info.value)
