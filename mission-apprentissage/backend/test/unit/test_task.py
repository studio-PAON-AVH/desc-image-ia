import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock

load_dotenv()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    return user


@pytest.fixture
def session(mocker):
    mock = mocker.MagicMock()
    mock.add = mocker.MagicMock(return_value=None)
    mock.commit = mocker.AsyncMock(return_value=None)
    mock.refresh = mocker.AsyncMock(return_value=None)
    mock.execute = mocker.AsyncMock(return_value=None)
    return mock


class TestTaskService:
    class TestGetModelKey:
        @pytest.mark.unit
        def test_get_model_key_salesforce(self):
            """Test que 'Salesforce BLIP' (nom réel en DB) retourne la clé salesforce_blip."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key("Salesforce BLIP") == "salesforce_blip"

        @pytest.mark.unit
        def test_get_model_key_florence(self):
            """Test que 'Florence-2' (nom réel en DB) retourne la clé florence2."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key("Florence-2") == "florence2"

        @pytest.mark.unit
        def test_get_model_key_git(self):
            """Test que 'GIT Large' (nom réel en DB) retourne la clé git_large."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key("GIT Large") == "git_large"

        @pytest.mark.unit
        def test_get_model_key_none(self):
            """Test que None retourne None."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key(None) is None

        @pytest.mark.unit
        def test_get_model_key_unknown(self):
            """Test qu'un nom inconnu est retourné tel quel."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key("unknown_model") == "unknown_model"

    class TestGetTaskDescriptions:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_descriptions_success(self, session):
            """Test que get_task_descriptions retourne les données complètes d'une tâche."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.status = "completed"

            mock_model_ia = MagicMock()
            mock_model_ia.name = "Salesforce/blip"

            mock_desc = MagicMock()
            mock_desc.id = 10
            mock_desc.description_text = "Un chat assis"
            mock_desc.modelIA = mock_model_ia
            mock_desc.is_written_by_ai = True
            mock_desc.is_written_by_human = False
            mock_desc.validated_by_human = False

            mock_image = MagicMock()
            mock_image.id = 5
            mock_image.image_file_name = "cat.jpg"
            mock_image.image_position_in_epub = 0
            mock_image.description = [mock_desc]

            # Premier execute : récupérer la tâche
            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = mock_task

            # Deuxième execute : récupérer les images
            mock_images_result = MagicMock()
            mock_images_result.scalars.return_value.all.return_value = [mock_image]

            session.execute = AsyncMock(side_effect=[mock_task_result, mock_images_result])

            from backend.tasks.service import get_task_descriptions

            result = await get_task_descriptions(session=session, task_id_redis="task-abc")

            assert result is not None
            assert result["task_id"] == "task-abc"
            assert result["status"] == "completed"
            assert result["total_images"] == 1
            assert len(result["images"]) == 1
            assert result["images"][0]["image_file_name"] == "cat.jpg"
            assert result["images"][0]["descriptions"][0]["description_text"] == "Un chat assis"
            assert result["images"][0]["descriptions"][0]["model_key"] == "salesforce_blip"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_descriptions_task_not_found(self, session):
            """Test que get_task_descriptions retourne None si la tâche est absente."""
            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_task_result)

            from backend.tasks.service import get_task_descriptions

            result = await get_task_descriptions(session=session, task_id_redis="inexistant")

            assert result is None

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_descriptions_no_images(self, session):
            """Test que get_task_descriptions retourne total_images=0 si aucune image."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.status = "completed"

            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = mock_task

            mock_images_result = MagicMock()
            mock_images_result.scalars.return_value.all.return_value = []

            session.execute = AsyncMock(side_effect=[mock_task_result, mock_images_result])

            from backend.tasks.service import get_task_descriptions

            result = await get_task_descriptions(session=session, task_id_redis="task-abc")

            assert result is not None
            assert result["total_images"] == 0
            assert result["images"] == []

    class TestValidateTaskDescriptions:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_validate_task_descriptions_task_not_found(self, session):
            """Test que validate_task_descriptions retourne None si la tâche est absente."""
            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_task_result)

            from backend.tasks.service import validate_task_descriptions

            result = await validate_task_descriptions(
                session=session, task_id_redis="inexistant", descriptions=[]
            )

            assert result is None
            session.commit.assert_not_called()

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_validate_task_descriptions_ai_model(self, session):
            """Test que la description IA est marquée validated_by_human=True."""
            mock_task = MagicMock()
            mock_task.id = 1

            mock_image = MagicMock()
            mock_image.id = 5

            mock_model = MagicMock()
            mock_model.id = 1
            mock_model.name = "Salesforce/blip"

            mock_existing_desc = MagicMock()
            mock_existing_desc.validated_by_human = False

            # execute calls: task, images, models, existing_desc, delete non-validated
            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = mock_task

            mock_images_result = MagicMock()
            mock_images_result.scalars.return_value.all.return_value = [mock_image]

            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = [mock_model]

            mock_desc_result = MagicMock()
            mock_desc_result.scalar_one_or_none.return_value = mock_existing_desc

            mock_delete_result = MagicMock()

            session.execute = AsyncMock(
                side_effect=[
                    mock_task_result,
                    mock_images_result,
                    mock_models_result,
                    mock_desc_result,
                    mock_delete_result,
                ]
            )

            desc_data = MagicMock()
            desc_data.image_index = 0
            desc_data.is_written_by_human = False
            desc_data.model = "salesforce"

            from backend.tasks.service import validate_task_descriptions

            result = await validate_task_descriptions(
                session=session, task_id_redis="task-abc", descriptions=[desc_data]
            )

            assert result is True
            assert mock_existing_desc.validated_by_human is True
            session.commit.assert_called_once()

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_validate_task_descriptions_human_written(self, session):
            """Test qu'une description humaine crée une nouvelle ImageDescription."""
            mock_task = MagicMock()
            mock_task.id = 1

            mock_image = MagicMock()
            mock_image.id = 5

            mock_model = MagicMock()
            mock_model.id = 1
            mock_model.name = "Salesforce/blip"

            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = mock_task

            mock_images_result = MagicMock()
            mock_images_result.scalars.return_value.all.return_value = [mock_image]

            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = [mock_model]

            mock_delete_result = MagicMock()

            session.execute = AsyncMock(
                side_effect=[
                    mock_task_result,
                    mock_images_result,
                    mock_models_result,
                    mock_delete_result,
                ]
            )

            desc_data = MagicMock()
            desc_data.image_index = 0
            desc_data.is_written_by_human = True
            desc_data.text = "Description écrite par un humain"

            from backend.tasks.service import validate_task_descriptions

            result = await validate_task_descriptions(
                session=session, task_id_redis="task-abc", descriptions=[desc_data]
            )

            assert result is True
            session.add.assert_called_once()
            session.commit.assert_called_once()

            added_desc = session.add.call_args[0][0]
            assert added_desc.is_written_by_human is True
            assert added_desc.is_written_by_ai is False
            assert added_desc.description_text == "Description écrite par un humain"
            assert added_desc.validated_by_human is True

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_validate_task_descriptions_image_index_out_of_bounds(self, session):
            """Test que validate_task_descriptions ignore les index hors limites."""
            mock_task = MagicMock()
            mock_task.id = 1

            mock_image = MagicMock()
            mock_image.id = 5

            mock_model = MagicMock()
            mock_model.id = 1
            mock_model.name = "Salesforce/blip"

            mock_task_result = MagicMock()
            mock_task_result.scalar_one_or_none.return_value = mock_task

            mock_images_result = MagicMock()
            mock_images_result.scalars.return_value.all.return_value = [mock_image]

            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = [mock_model]

            session.execute = AsyncMock(
                side_effect=[
                    mock_task_result,
                    mock_images_result,
                    mock_models_result,
                ]
            )

            desc_data = MagicMock()
            desc_data.image_index = 99  # hors limites (seulement 1 image)

            from backend.tasks.service import validate_task_descriptions

            result = await validate_task_descriptions(
                session=session, task_id_redis="task-abc", descriptions=[desc_data]
            )

            assert result is True
            session.add.assert_not_called()
            session.commit.assert_called_once()
