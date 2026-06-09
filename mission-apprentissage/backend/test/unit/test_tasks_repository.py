# tests/test_tasks_repository.py
import pytest
from unittest.mock import MagicMock


class TestUpsertFinalDescription:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_description_when_none_exists(self, mock_session):
        """Sans description existante, upsert_final_description ajoute une nouvelle ligne."""
        from backend.tasks.repository import upsert_final_description

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        desc = await upsert_final_description(
            mock_session,
            image_id=3,
            user_id=7,
            model_ia_id=None,
            text="Mon texte",
        )

        mock_session.add.assert_called_once_with(desc)
        assert desc.image_id == 3
        assert desc.user_id == 7
        assert desc.model_ia_id is None
        assert desc.description_text == "Mon texte"
        assert desc.validated_by_human is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_updates_description_when_existing(self, mock_session):
        """Si une DescriptionFinale existe déjà, elle est mise à jour sans appeler session.add."""
        from backend.tasks.repository import upsert_final_description

        existing = MagicMock()
        existing.validated_by_human = False
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = result_mock

        desc = await upsert_final_description(
            mock_session,
            image_id=3,
            user_id=7,
            model_ia_id=2,
            text="Nouveau texte",
        )

        assert desc is existing
        assert existing.user_id == 7
        assert existing.model_ia_id == 2
        assert existing.description_text == "Nouveau texte"
        assert existing.validated_by_human is True
        mock_session.add.assert_not_called()
