# tests/test_tasks_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestFindTaskByRedisId:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_task_when_found(self, mock_session):
        mock_task = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_session.execute.return_value = mock_result

        from backend.tasks.repository import find_task_by_redis_id

        result = await find_task_by_redis_id(mock_session, "task-abc")

        assert result is mock_task

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        from backend.tasks.repository import find_task_by_redis_id

        result = await find_task_by_redis_id(mock_session, "unknown")

        assert result is None


class TestFindAllTasks:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_rows(self, mock_session):
        mock_row = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row, mock_row]
        mock_session.execute.return_value = mock_result

        from backend.tasks.repository import find_all_tasks

        result = await find_all_tasks(mock_session, limit=10, offset=0)

        assert len(result) == 2


class TestFindImagesWithDescriptions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_images(self, mock_session):
        mock_image = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_image]
        mock_session.execute.return_value = mock_result

        from backend.tasks.repository import find_images_with_descriptions

        result = await find_images_with_descriptions(mock_session, task_id=1)

        assert result == [mock_image]


class TestDeleteAiDescriptions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executes_delete(self, mock_session):
        from backend.tasks.repository import delete_ai_descriptions_for_image

        await delete_ai_descriptions_for_image(mock_session, image_id=5)

        mock_session.execute.assert_called_once()


class TestCreateHumanDescription:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_description_with_correct_flags(self, mock_session):
        from backend.tasks.repository import create_human_description

        desc = await create_human_description(mock_session, image_id=3, text="Mon texte")

        mock_session.add.assert_called_once_with(desc)
        assert desc.image_id == 3
        assert desc.description_text == "Mon texte"
        assert desc.is_written_by_human is True
        assert desc.is_written_by_ai is False
        assert desc.validated_by_human is True
        assert desc.model_ia_id is None
