# tests/test_auth_schemas.py
import pytest
from pydantic import ValidationError


def test_user_create_valid():
    from backend.auth.schemas import UserCreate

    user = UserCreate(username="alice", email="alice@example.com", password="secret123")
    assert user.username == "alice"
    assert user.email == "alice@example.com"


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


def test_user_create_invalid_email():
    from backend.auth.schemas import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="not-an-email", password="secret123")


def test_user_login_valid():
    from backend.auth.schemas import UserLogin

    login = UserLogin(email="alice@example.com", password="secret123")
    assert login.email == "alice@example.com"


def test_user_response_fields():
    from backend.auth.schemas import UserResponse
    from datetime import datetime

    resp = UserResponse(
        username="alice",
        email="alice@example.com",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert resp.username == "alice"
