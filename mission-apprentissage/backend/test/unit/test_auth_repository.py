# tests/test_auth_repository.py
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock


class TestCreateUser:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_user_with_default_role(self, mock_session):
        from backend.auth.repository import create_user

        result = await create_user(mock_session, "alice", "alice@example.com", "hash")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.username == "alice"
        assert added.email == "alice@example.com"
        assert added.password_hash == "hash"
        assert added.role == "user"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_admin_user(self, mock_session):
        from backend.auth.repository import create_user

        await create_user(mock_session, "admin", "admin@example.com", "hash", role="admin")

        added = mock_session.add.call_args[0][0]
        assert added.role == "admin"


class TestCreateRefreshTokenRecord:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_token_record(self, mock_session):
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)

        from backend.auth.repository import create_refresh_token_record

        await create_refresh_token_record(mock_session, "tok123", 42, expires_at)

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.token == "tok123"
        assert added.user_id == 42
        assert added.expires_at == expires_at


class TestRevokeRefreshTokenRecord:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sets_revoked_true(self, mock_session):
        mock_record = MagicMock()
        mock_record.revoked = False
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_record
        mock_session.execute.return_value = mock_result

        from backend.auth.repository import revoke_refresh_token_record

        await revoke_refresh_token_record(mock_session, "tok123")

        assert mock_record.revoked is True
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_nothing_when_token_absent(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        from backend.auth.repository import revoke_refresh_token_record

        await revoke_refresh_token_record(mock_session, "unknown")

        mock_session.commit.assert_not_called()
