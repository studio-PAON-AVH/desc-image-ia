import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def session(mocker):
    mock = mocker.MagicMock()
    mock.add = mocker.MagicMock(return_value=None)
    mock.commit = mocker.AsyncMock(return_value=None)
    mock.refresh = mocker.AsyncMock(return_value=None)
    mock.execute = mocker.AsyncMock(return_value=None)
    return mock


def make_async_session_cm(session_mock):
    """Crée un context manager async simulant async_session()."""
    cm = AsyncMock()
    cm.__aenter__.return_value = session_mock
    cm.__aexit__.return_value = None
    return cm


class TestRecoverStuckTasks:

    class TestNoStuckTasks:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_tasks_does_nothing(self, mocker):
            """Test que recover_stuck_tasks ne fait rien s'il n'y a pas de tâches bloquées."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)
            mocker.patch("backend.worker.worker.r")

            from backend.worker.worker import recover_stuck_tasks
            await recover_stuck_tasks(state=None)

            mock_update.assert_not_called()

    class TestStuckTaskWithNoRedisData:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_redis_data_marks_failed(self, mocker):
            """Test qu'une tâche bloquée sans données Redis est marquée comme failed."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.task_id_redis = "redis-key-1"

            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_task]
            mock_session.execute = AsyncMock(return_value=mock_result)

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = None
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import recover_stuck_tasks
            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "failed")

    class TestStuckTaskWithRedisDataAndMissingFile:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_file_not_found_marks_failed(self, mocker):
            """Test qu'une tâche dont le fichier epub n'existe plus est marquée comme failed."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.task_id_redis = "redis-key-1"

            mock_epub = MagicMock()
            mock_epub.id = 10

            mock_session = AsyncMock()
            mock_result_tasks = MagicMock()
            mock_result_tasks.scalars.return_value.all.return_value = [mock_task]
            mock_result_epub = MagicMock()
            mock_result_epub.scalar_one_or_none.return_value = mock_epub
            mock_session.execute = AsyncMock(side_effect=[mock_result_tasks, mock_result_epub])

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=False)
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import recover_stuck_tasks
            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "failed")
            mock_redis.set.assert_called_once()
            error_payload = json.loads(mock_redis.set.call_args[0][1])
            assert "error" in error_payload

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_epub_in_db_marks_failed(self, mocker):
            """Test qu'une tâche bloquée sans epub en BDD est marquée comme failed."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.task_id_redis = "redis-key-1"

            mock_session = AsyncMock()
            mock_result_tasks = MagicMock()
            mock_result_tasks.scalars.return_value.all.return_value = [mock_task]
            mock_result_epub = MagicMock()
            mock_result_epub.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(side_effect=[mock_result_tasks, mock_result_epub])

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import recover_stuck_tasks
            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "failed")
            mock_redis.set.assert_called_once()
            error_payload = json.loads(mock_redis.set.call_args[0][1])
            assert "error" in error_payload

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_epub_path_in_redis_marks_failed(self, mocker):
            """Test qu'une tâche sans epub_path dans Redis est marquée comme failed."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.task_id_redis = "redis-key-1"

            mock_epub = MagicMock()
            mock_epub.id = 10

            mock_session = AsyncMock()
            mock_result_tasks = MagicMock()
            mock_result_tasks.scalars.return_value.all.return_value = [mock_task]
            mock_result_epub = MagicMock()
            mock_result_epub.scalar_one_or_none.return_value = mock_epub
            mock_session.execute = AsyncMock(side_effect=[mock_result_tasks, mock_result_epub])

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"autre_cle": "valeur"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import recover_stuck_tasks
            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "failed")

    class TestStuckTaskRecovered:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_recovers_task_successfully(self, mocker):
            """Test qu'une tâche bloquée récupérable est relancée avec succès."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.task_id_redis = "redis-key-1"

            mock_epub = MagicMock()
            mock_epub.id = 10

            mock_session = AsyncMock()
            mock_result_tasks = MagicMock()
            mock_result_tasks.scalars.return_value.all.return_value = [mock_task]
            mock_result_epub = MagicMock()
            mock_result_epub.scalar_one_or_none.return_value = mock_epub
            mock_session.execute = AsyncMock(side_effect=[mock_result_tasks, mock_result_epub])

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import process_epub_describe, recover_stuck_tasks
            mock_kiq = mocker.patch.object(process_epub_describe, "kiq", new_callable=AsyncMock)

            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "pending")
            mock_kiq.assert_called_once_with("/path/to/file.epub", "redis-key-1", 1, 10)


class TestProcessEpubDescribe:

    class TestHappyPath:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_full_pipeline_success(self, mocker):
            """Test le pipeline complet de traitement d'un EPUB avec succès."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            image_paths = ["/tmp/img1.png", "/tmp/img2.png"]
            temp_folder = "/tmp/epub_extract"
            fake_images = [MagicMock(), MagicMock()]
            fake_descriptions = {"images": {"image_0": {}, "image_1": {}}, "total_images": 2, "time": 1.0}

            mock_session = AsyncMock()
            mock_model_blip = MagicMock()
            mock_model_blip.name = "Salesforce BLIP"
            mock_model_blip.id = 1
            mock_model_florence = MagicMock()
            mock_model_florence.name = "Florence-2"
            mock_model_florence.id = 2
            mock_model_git = MagicMock()
            mock_model_git.name = "GIT Large"
            mock_model_git.id = 3
            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = [mock_model_blip, mock_model_florence, mock_model_git]
            mock_session.execute = AsyncMock(return_value=mock_models_result)

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.extract_images_epub", return_value=(image_paths, temp_folder))
            mock_save_images = mocker.patch("backend.worker.worker.save_images", new_callable=AsyncMock, return_value=fake_images)
            mock_get_describe = mocker.patch("backend.worker.worker.get_image_describe", new_callable=AsyncMock, return_value=fake_descriptions)
            mock_save_descriptions = mocker.patch("backend.worker.worker.save_image_descriptions", new_callable=AsyncMock)
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)
            mock_rmtree = mocker.patch("backend.worker.worker.shutil.rmtree")
            mocker.patch("builtins.open", mocker.mock_open(read_data=b"fake_image_bytes"))

            from backend.worker.worker import process_epub_describe
            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mock_update.assert_any_call(mock_session, db_task_id, "in_progress")
            mock_save_images.assert_called_once_with(mock_session, db_task_id, epub_id, image_paths)
            mock_get_describe.assert_called_once()
            mock_save_descriptions.assert_called_once()
            mock_update.assert_any_call(mock_session, db_task_id, "completed")
            mock_redis.set.assert_called_once()
            redis_payload = json.loads(mock_redis.set.call_args[0][1])
            assert redis_payload["epub_path"] == epub_path
            assert "descriptions" in redis_payload
            mock_rmtree.assert_called_once_with(temp_folder)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_images_are_encoded_in_base64(self, mocker):
            """Test que les images sont bien encodées en base64 avant l'appel aux modèles IA."""
            import base64

            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            image_paths = ["/tmp/img1.png"]
            fake_images = [MagicMock()]
            fake_descriptions = {"images": {}, "total_images": 1, "time": 0.5}
            fake_img_bytes = b"image_bytes"

            mock_session = AsyncMock()
            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_models_result)

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.extract_images_epub", return_value=(image_paths, None))
            mocker.patch("backend.worker.worker.save_images", new_callable=AsyncMock, return_value=fake_images)
            mock_get_describe = mocker.patch("backend.worker.worker.get_image_describe", new_callable=AsyncMock, return_value=fake_descriptions)
            mocker.patch("backend.worker.worker.save_image_descriptions", new_callable=AsyncMock)
            mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)
            mocker.patch("builtins.open", mocker.mock_open(read_data=fake_img_bytes))

            from backend.worker.worker import process_epub_describe
            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            img_list_arg = mock_get_describe.call_args[0][0]
            assert len(img_list_arg) == 1
            assert img_list_arg[0] == base64.b64encode(fake_img_bytes).decode("utf-8")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_temp_folder_skips_cleanup(self, mocker):
            """Test que shutil.rmtree n'est pas appelé si temp_folder est None."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            image_paths = ["/tmp/img1.png"]
            fake_images = [MagicMock()]
            fake_descriptions = {"images": {}, "total_images": 1, "time": 0.5}

            mock_session = AsyncMock()
            mock_models_result = MagicMock()
            mock_models_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_models_result)

            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.extract_images_epub", return_value=(image_paths, None))
            mocker.patch("backend.worker.worker.save_images", new_callable=AsyncMock, return_value=fake_images)
            mocker.patch("backend.worker.worker.get_image_describe", new_callable=AsyncMock, return_value=fake_descriptions)
            mocker.patch("backend.worker.worker.save_image_descriptions", new_callable=AsyncMock)
            mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)
            mock_rmtree = mocker.patch("backend.worker.worker.shutil.rmtree")
            mocker.patch("builtins.open", mocker.mock_open(read_data=b"fake"))

            from backend.worker.worker import process_epub_describe
            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mock_rmtree.assert_not_called()

    class TestErrorHandling:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_exception_marks_task_failed(self, mocker):
            """Test qu'une exception marque la tâche comme failed."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            mock_session = AsyncMock()
            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mocker.patch("backend.worker.worker.extract_images_epub", side_effect=RuntimeError("Fichier corrompu"))
            mocker.patch("backend.worker.worker.r")
            mock_update = mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import process_epub_describe
            with pytest.raises(RuntimeError):
                await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mock_update.assert_any_call(mock_session, db_task_id, "failed")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_exception_stores_error_in_redis(self, mocker):
            """Test que le message d'erreur est stocké dans Redis en cas d'exception."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7
            error_message = "Fichier corrompu"

            mock_session = AsyncMock()
            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mocker.patch("backend.worker.worker.extract_images_epub", side_effect=RuntimeError(error_message))
            mock_redis = mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import process_epub_describe
            with pytest.raises(RuntimeError):
                await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mock_redis.set.assert_called_once()
            error_payload = json.loads(mock_redis.set.call_args[0][1])
            assert "error" in error_payload
            assert error_message in error_payload["error"]

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_exception_is_reraised(self, mocker):
            """Test que l'exception est bien re-levée après le traitement d'erreur."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            mock_session = AsyncMock()
            mocker.patch("backend.worker.worker.async_session", return_value=make_async_session_cm(mock_session))
            mocker.patch("backend.worker.worker.extract_images_epub", side_effect=ValueError("Erreur inattendue"))
            mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import process_epub_describe
            with pytest.raises(ValueError, match="Erreur inattendue"):
                await process_epub_describe(epub_path, task_id, db_task_id, epub_id)
