# tests/test_auth_repository.py
import pytest
from unittest.mock import MagicMock


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
