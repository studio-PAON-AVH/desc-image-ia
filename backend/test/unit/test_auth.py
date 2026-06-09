import pytest
import os
import datetime

from unittest.mock import AsyncMock, MagicMock
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import timedelta

from backend.auth.service import (
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    authenticate_user,
    hash_password,
    verify_password,
)
from backend.auth.middleware import get_current_user, is_admin


# ── Service — tokens ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_create_access_token():
    """Token JWT bien formé avec sub et exp."""
    token = create_access_token({"sub": "testuser@example.com"})
    assert isinstance(token, str)
    decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
    assert decoded["sub"] == "testuser@example.com"
    assert "exp" in decoded


@pytest.mark.unit
def test_create_access_token_with_expires_delta():
    """Token créé avec un expires_delta explicite."""
    token = create_access_token(
        {"sub": "testuser@example.com"}, expires_delta=timedelta(minutes=30)
    )
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_refresh_token():
    """create_refresh_token retourne un token string et appelle add + commit."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # Session.add est synchrone
    mock_result = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    token = await create_refresh_token("testuser@example.com", mock_db)

    assert isinstance(token, str)
    assert len(token) > 0
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_refresh_token_valid():
    """validate_refresh_token retourne l'email si le token est valide."""
    mock_db = AsyncMock()
    mock_refresh = MagicMock()
    mock_refresh.user_id = 1
    mock_user = MagicMock()
    mock_user.email = "testuser@example.com"

    mock_result_refresh = MagicMock()
    mock_result_refresh.scalars.return_value.first.return_value = mock_refresh
    mock_result_user = MagicMock()
    mock_result_user.scalars.return_value.first.return_value = mock_user
    mock_db.execute.side_effect = [mock_result_refresh, mock_result_user]

    result = await validate_refresh_token("valid_token", mock_db)

    assert result == "testuser@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_refresh_token_not_found():
    """validate_refresh_token retourne None si le token n'existe pas ou est expiré."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = await validate_refresh_token("unknown_token", mock_db)

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_refresh_token_sets_revoked():
    """revoke_refresh_token met revoked=True et commite."""
    mock_db = AsyncMock()
    mock_refresh = MagicMock()
    mock_refresh.revoked = False
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_refresh
    mock_db.execute.return_value = mock_result

    await revoke_refresh_token("valid_token", mock_db)

    assert mock_refresh.revoked is True
    mock_db.commit.assert_called_once()


# ── Service — password ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_hash_and_verify_password_valid():
    """Le hash est différent du mot de passe en clair et la vérification réussit."""
    hashed = hash_password("testpassword")
    assert hashed != "testpassword"
    assert verify_password("testpassword", hashed) is True


@pytest.mark.unit
def test_verify_password_wrong():
    """Un mauvais mot de passe ne passe pas la vérification."""
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


# ── Service — utilisateur ─────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_valid(mocker):
    """authenticate_user retourne l'utilisateur si email + mot de passe corrects."""
    mock_user = MagicMock()
    mock_user.email = "testuser@example.com"
    mock_user.password_hash = "fake_hash"
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mocker.patch("backend.auth.service.verify_password", return_value=True)

    result = await authenticate_user(mock_db, "testuser@example.com", "testpassword")

    assert result.email == "testuser@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """authenticate_user retourne None si l'utilisateur est absent."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await authenticate_user(mock_db, "unknown@example.com", "pass")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(mocker):
    """authenticate_user retourne None si le mot de passe est incorrect."""
    mock_user = MagicMock()
    mock_user.password_hash = "fake_hash"
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mocker.patch("backend.auth.service.verify_password", return_value=False)

    result = await authenticate_user(mock_db, "testuser@example.com", "wrongpassword")

    assert result is None


# ── Middleware — get_current_user ─────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_valid_token(mocker):
    """Token valide → utilisateur retourné."""
    mock_user = MagicMock()
    mocker.patch("backend.auth.middleware.jwt.decode", return_value={"sub": "testuser@example.com"})
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "fake_valid_token"
    mock_request.headers.get.return_value = ""

    result = await get_current_user(mock_request, mock_db)

    assert result == mock_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_expired_token(mocker):
    """Token expiré → HTTPException 401."""
    mocker.patch("backend.auth.middleware.jwt.decode", side_effect=ExpiredSignatureError)
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "expired_token"
    mock_request.headers.get.return_value = ""

    with pytest.raises(Exception) as exc_info:
        await get_current_user(mock_request, AsyncMock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mocker):
    """Token invalide → HTTPException 401."""
    mocker.patch("backend.auth.middleware.jwt.decode", side_effect=InvalidTokenError)
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "invalid_token"
    mock_request.headers.get.return_value = ""

    with pytest.raises(Exception) as exc_info:
        await get_current_user(mock_request, AsyncMock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_no_sub_in_payload(mocker):
    """Payload sans sub → HTTPException 401."""
    mocker.patch("backend.auth.middleware.jwt.decode", return_value={"sub": None})
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "token_without_sub"
    mock_request.headers.get.return_value = ""

    with pytest.raises(Exception) as exc_info:
        await get_current_user(mock_request, AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mocker):
    """Token valide mais utilisateur absent en DB → HTTPException 401."""
    mocker.patch("backend.auth.middleware.jwt.decode", return_value={"sub": "unknown@example.com"})
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "valid_token"
    mock_request.headers.get.return_value = ""

    with pytest.raises(Exception) as exc_info:
        await get_current_user(mock_request, mock_db)

    assert exc_info.value.status_code == 401


# ── Middleware — is_admin ─────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_admin_valid():
    """is_admin ne lève pas d'exception si l'utilisateur est admin."""
    mock_user = MagicMock()
    mock_user.role = "admin"
    await is_admin(mock_user)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_admin_non_admin():
    """is_admin lève HTTPException 403 si l'utilisateur n'est pas admin."""
    mock_user = MagicMock()
    mock_user.role = "user"

    with pytest.raises(Exception) as exc_info:
        await is_admin(mock_user)

    assert exc_info.value.status_code == 403
