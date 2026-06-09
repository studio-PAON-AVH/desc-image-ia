import pytest
import json
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.responses import JSONResponse

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


class TestTaskController:

    class TestGetAllTasks:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_all_tasks_success(self, session):
            """Test que get_all_tasks retourne une liste de tâches."""
            mock_task1 = MagicMock()
            mock_task1._mapping = {"id": 1, "status": "completed", "task_id_redis": "abc"}
            mock_task2 = MagicMock()
            mock_task2._mapping = {"id": 2, "status": "pending", "task_id_redis": "def"}

            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_task1, mock_task2]
            session.execute = AsyncMock(return_value=mock_result)

            from backend.controllers.task_controller import get_all_tasks
            result = await get_all_tasks(db=session)

            assert "tasks" in result
            assert len(result["tasks"]) == 2
            assert result["tasks"][0]["id"] == 1
            assert result["tasks"][1]["id"] == 2

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_all_tasks_empty(self, session):
            """Test que get_all_tasks retourne une liste vide si aucune tâche."""
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            session.execute = AsyncMock(return_value=mock_result)

            from backend.controllers.task_controller import get_all_tasks
            result = await get_all_tasks(db=session)

            assert "tasks" in result
            assert result["tasks"] == []

    class TestGetTaskResult:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_success(self, mocker, mock_user, session):
            """Test que get_task_result retourne le résultat redis quand tout est OK."""
            mock_task = MagicMock()
            mock_task.user_id = 1
            mock_task.task_id_redis = "task-123"

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            redis_data = json.dumps({"image_0": "Un chat"}).encode("utf-8")
            mock_redis = MagicMock()
            mock_redis.get.return_value = redis_data
            mocker.patch("backend.controllers.task_controller.redis_dev", mock_redis)

            from backend.controllers.task_controller import get_task_result
            result = await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert "result" in result
            assert result["result"]["image_0"] == "Un chat"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_task_not_found(self, mock_user, session):
            """Test que get_task_result lève HTTPException 404 si la tâche est absente."""
            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = None
            session.execute = AsyncMock(return_value=mock_db_result)

            from backend.controllers.task_controller import get_task_result
            with pytest.raises(HTTPException) as exc_info:
                await get_task_result(task_id="inexistant", current_user=mock_user, db=session)

            assert exc_info.value.status_code == 404

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_forbidden(self, mock_user, session):
            """Test que get_task_result lève HTTPException 403 si l'utilisateur n'est pas propriétaire."""
            mock_task = MagicMock()
            mock_task.user_id = 99  # différent de mock_user.id = 1

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            from backend.controllers.task_controller import get_task_result
            with pytest.raises(HTTPException) as exc_info:
                await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert exc_info.value.status_code == 403

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_redis_not_found(self, mocker, mock_user, session):
            """Test que get_task_result lève HTTPException 404 si redis ne contient pas le résultat."""
            mock_task = MagicMock()
            mock_task.user_id = 1

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mocker.patch("backend.controllers.task_controller.redis_dev", mock_redis)

            from backend.controllers.task_controller import get_task_result
            with pytest.raises(HTTPException) as exc_info:
                await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert exc_info.value.status_code == 404

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_decode_error(self, mocker, mock_user, session):
            """Test que get_task_result lève HTTPException 500 si le décodage JSON échoue."""
            mock_task = MagicMock()
            mock_task.user_id = 1

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            mock_redis = MagicMock()
            mock_redis.get.return_value = b"invalid json {"
            mocker.patch("backend.controllers.task_controller.redis_dev", mock_redis)

            from backend.controllers.task_controller import get_task_result
            with pytest.raises(HTTPException) as exc_info:
                await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert exc_info.value.status_code == 500

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_error_in_result(self, mocker, mock_user, session):
            """Test que get_task_result lève HTTPException 500 si le résultat contient une erreur."""
            mock_task = MagicMock()
            mock_task.user_id = 1

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            mock_redis = MagicMock()
            mock_redis.get.return_value = json.dumps({"error": "Modèle indisponible"}).encode("utf-8")
            mocker.patch("backend.controllers.task_controller.redis_dev", mock_redis)

            from backend.controllers.task_controller import get_task_result
            with pytest.raises(HTTPException) as exc_info:
                await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert exc_info.value.status_code == 500

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_task_result_pending(self, mocker, mock_user, session):
            """Test que get_task_result retourne 202 si la tâche est en attente."""
            mock_task = MagicMock()
            mock_task.user_id = 1

            mock_db_result = MagicMock()
            mock_db_result.scalars.return_value.first.return_value = mock_task
            session.execute = AsyncMock(return_value=mock_db_result)

            mock_redis = MagicMock()
            mock_redis.get.return_value = json.dumps({"status": "en attente"}).encode("utf-8")
            mocker.patch("backend.controllers.task_controller.redis_dev", mock_redis)

            from backend.controllers.task_controller import get_task_result
            result = await get_task_result(task_id="task-123", current_user=mock_user, db=session)

            assert isinstance(result, JSONResponse)
            assert result.status_code == 202


class TestTaskService:

    class TestGetModelKey:

        @pytest.mark.unit
        def test_get_model_key_salesforce(self):
            """Test que Salesforce/blip retourne la clé salesforce_blip."""
            from backend.services.task_service import _get_model_key
            assert _get_model_key("Salesforce/blip") == "salesforce_blip"

        @pytest.mark.unit
        def test_get_model_key_florence(self):
            """Test que Florence-2-large retourne la clé florence2."""
            from backend.services.task_service import _get_model_key
            assert _get_model_key("Florence-2-large") == "florence2"

        @pytest.mark.unit
        def test_get_model_key_git(self):
            """Test que microsoft/git-large retourne la clé git_large."""
            from backend.services.task_service import _get_model_key
            assert _get_model_key("microsoft/git-large") == "git_large"

        @pytest.mark.unit
        def test_get_model_key_none(self):
            """Test que None retourne None."""
            from backend.services.task_service import _get_model_key
            assert _get_model_key(None) is None

        @pytest.mark.unit
        def test_get_model_key_unknown(self):
            """Test qu'un nom inconnu est retourné tel quel."""
            from backend.services.task_service import _get_model_key
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

            from backend.services.task_service import get_task_descriptions
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

            from backend.services.task_service import get_task_descriptions
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

            from backend.services.task_service import get_task_descriptions
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

            from backend.services.task_service import validate_task_descriptions
            result = await validate_task_descriptions(
                session=session,
                task_id_redis="inexistant",
                descriptions=[]
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

            session.execute = AsyncMock(side_effect=[
                mock_task_result,
                mock_images_result,
                mock_models_result,
                mock_desc_result,
                mock_delete_result,
            ])

            desc_data = MagicMock()
            desc_data.image_index = 0
            desc_data.is_written_by_human = False
            desc_data.model = "salesforce"

            from backend.services.task_service import validate_task_descriptions
            result = await validate_task_descriptions(
                session=session,
                task_id_redis="task-abc",
                descriptions=[desc_data]
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

            session.execute = AsyncMock(side_effect=[
                mock_task_result,
                mock_images_result,
                mock_models_result,
                mock_delete_result,
            ])

            desc_data = MagicMock()
            desc_data.image_index = 0
            desc_data.is_written_by_human = True
            desc_data.text = "Description écrite par un humain"

            from backend.services.task_service import validate_task_descriptions
            result = await validate_task_descriptions(
                session=session,
                task_id_redis="task-abc",
                descriptions=[desc_data]
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

            session.execute = AsyncMock(side_effect=[
                mock_task_result,
                mock_images_result,
                mock_models_result,
            ])

            desc_data = MagicMock()
            desc_data.image_index = 99  # hors limites (seulement 1 image)

            from backend.services.task_service import validate_task_descriptions
            result = await validate_task_descriptions(
                session=session,
                task_id_redis="task-abc",
                descriptions=[desc_data]
            )

            assert result is True
            session.add.assert_not_called()
            session.commit.assert_called_once()