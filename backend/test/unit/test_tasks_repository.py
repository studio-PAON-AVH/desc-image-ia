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


class TestDeleteEpubAndChildren:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deletes_children_and_returns_storage_locations(self, mock_session):
        """Retourne les emplacements MinIO des images pour que l'appelant
        (service d'annulation) supprime aussi les objets, et supprime en
        cascade descriptions + images + epub."""
        from backend.tasks.repository import delete_epub_and_children

        image1 = MagicMock(id=1, storage_bucket="bucket", storage_object_key="key1")
        image2 = MagicMock(id=2, storage_bucket="bucket", storage_object_key="key2")
        images_result = MagicMock()
        images_result.scalars.return_value.all.return_value = [image1, image2]
        mock_session.execute.return_value = images_result

        storage_locations = await delete_epub_and_children(mock_session, task_id=99)

        assert storage_locations == [("bucket", "key1"), ("bucket", "key2")]
        mock_session.commit.assert_called_once()
        # find_images_by_task + delete(DescriptionByIA) + delete(DescriptionFinale)
        # + delete(Images) + delete(Epub)
        assert mock_session.execute.call_count == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_images_without_storage_location_are_excluded(self, mock_session):
        """Une image jamais uploadée sur MinIO (storage_bucket/key manquants)
        n'apparaît pas dans les emplacements à nettoyer."""
        from backend.tasks.repository import delete_epub_and_children

        image_no_storage = MagicMock(id=3, storage_bucket=None, storage_object_key=None)
        images_result = MagicMock()
        images_result.scalars.return_value.all.return_value = [image_no_storage]
        mock_session.execute.return_value = images_result

        storage_locations = await delete_epub_and_children(mock_session, task_id=99)

        assert storage_locations == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_images_only_deletes_epub(self, mock_session):
        """Sans image, seul l'Epub est supprimé (pas de delete DescriptionByIA
        / DescriptionFinale / Images inutiles)."""
        from backend.tasks.repository import delete_epub_and_children

        images_result = MagicMock()
        images_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = images_result

        storage_locations = await delete_epub_and_children(mock_session, task_id=99)

        assert storage_locations == []
        # find_images_by_task + delete(Epub) seulement
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()
