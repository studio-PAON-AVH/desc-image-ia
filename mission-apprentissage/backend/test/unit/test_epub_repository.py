# tests/test_epub_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestCreateTask:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_task_with_pending_status(self, mock_session):
        from backend.epub.repository import create_task

        result = await create_task(mock_session, "redis-uuid-1", user_id=7)

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.task_id_redis == "redis-uuid-1"
        assert added.user_id == 7
        assert added.status == "pending"
        assert added.total_images == 0
        mock_session.commit.assert_called_once()


class TestCreateEpub:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_epub_with_uploaded_status(self, mock_session):
        from backend.epub.repository import create_epub

        await create_epub(mock_session, task_id=3, file_name="book.epub")

        added = mock_session.add.call_args[0][0]
        assert added.task_id == 3
        assert added.file_name == "book.epub"
        assert added.status == "uploaded"


class TestCreateImagesBatch:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_one_image_per_path(self, mock_session):
        from backend.epub.repository import create_images_batch

        paths = ["/tmp/a.jpg", "/tmp/b.jpg", "/tmp/c.jpg"]
        await create_images_batch(mock_session, task_id=1, epub_id=2, image_paths=paths)

        assert mock_session.add.call_count == 3
        calls = [c[0][0] for c in mock_session.add.call_args_list]
        assert calls[0].image_file_name == "a.jpg"
        assert calls[0].image_position_in_epub == 0
        assert calls[1].image_position_in_epub == 1
        assert calls[2].image_position_in_epub == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_paths(self, mock_session):
        from backend.epub.repository import create_images_batch

        result = await create_images_batch(mock_session, task_id=1, epub_id=2, image_paths=[])

        assert result == []
        mock_session.add.assert_not_called()


class TestCreateImageDescriptionsBatch:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_description_for_each_model(self, mock_session):
        mock_image = MagicMock()
        mock_image.id = 10

        results = {
            "images": {
                "image_0": {
                    "salesforce_blip": {"french_description": "Un chien"},
                    "florence2": {"french_description": "Un chien assis"},
                    "git_large": None,
                }
            }
        }
        model_ia_mapping = {"salesforce_blip": 1, "florence2": 2, "git_large": 3}

        from backend.epub.repository import create_image_descriptions_batch

        await create_image_descriptions_batch(mock_session, [mock_image], results, model_ia_mapping)

        # salesforce_blip et florence2 ont une description, git_large est None → 2 add
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_missing_image_key(self, mock_session):
        mock_image = MagicMock()
        mock_image.id = 10

        results = {"images": {}}  # image_0 absent
        model_ia_mapping = {"salesforce_blip": 1}

        from backend.epub.repository import create_image_descriptions_batch

        await create_image_descriptions_batch(mock_session, [mock_image], results, model_ia_mapping)

        mock_session.add.assert_not_called()


class TestUpdateTaskStatus:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executes_update_and_commits(self, mock_session):
        from backend.epub.repository import update_task_status

        await update_task_status(mock_session, db_task_id=5, status="completed")

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
