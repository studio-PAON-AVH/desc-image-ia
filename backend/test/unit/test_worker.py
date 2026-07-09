import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock


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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )
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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = None
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=False)
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"autre_cle": "valeur"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

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

            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mock_redis = mocker.patch("backend.worker.worker.r")
            mock_redis.get.return_value = json.dumps({"epub_path": "/path/to/file.epub"}).encode()
            mocker.patch("os.path.exists", return_value=True)
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

            from backend.worker.worker import process_epub_describe, recover_stuck_tasks

            mock_kiq = mocker.patch.object(process_epub_describe, "kiq", new_callable=AsyncMock)

            await recover_stuck_tasks(state=None)

            mock_update.assert_called_once_with(mock_session, 1, "pending")
            mock_kiq.assert_called_once_with("/path/to/file.epub", "redis-key-1", 1, 10)


def _setup_process_epub_mocks(mocker, image_paths, temp_folder, fake_images, models=None):
    """Mocke les dépendances communes de process_epub_describe (orchestrateur).

    Fonction de module (pas une méthode) : les classes TestHappyPath /
    TestErrorHandling sont imbriquées dans TestProcessEpubDescribe mais
    n'héritent pas de ses méthodes (l'imbrication Python n'implique pas
    l'héritage), donc `self._setup_common` n'y serait pas résolu.
    """
    mock_session = AsyncMock()
    mock_models_result = MagicMock()
    mock_models_result.scalars.return_value.all.return_value = models or []
    mock_session.execute = AsyncMock(return_value=mock_models_result)

    mocker.patch(
        "backend.worker.worker.async_session",
        return_value=make_async_session_cm(mock_session),
    )
    mock_redis = mocker.patch("backend.worker.worker.r")
    mocker.patch(
        "backend.worker.worker.extract_images_epub", return_value=(image_paths, temp_folder)
    )
    mock_save_images = mocker.patch(
        "backend.worker.worker.save_images", new_callable=AsyncMock, return_value=fake_images
    )
    mock_set_total = mocker.patch(
        "backend.worker.worker.set_total_images", new_callable=AsyncMock
    )
    mock_update = mocker.patch(
        "backend.worker.worker.update_task_status", new_callable=AsyncMock
    )
    mock_rmtree = mocker.patch("backend.worker.worker.shutil.rmtree")
    mocker.patch(
        "backend.worker.worker.storage_minio",
        return_value=("bucket", [f"key{i}" for i in range(len(image_paths))]),
    )
    mocker.patch("backend.worker.worker.save_images_storage", new_callable=AsyncMock)
    mock_session.get = AsyncMock(return_value=MagicMock(file_name="book.epub"))

    # Le fan-out indexe MODEL_BATCH_TASKS par clé modèle : on remplace le
    # dict entier (plutôt que les noms individuels describe_batch_*) pour
    # que le patch soit bien vu par process_epub_describe, et pour éviter
    # tout .kiq() réel vers Redis dans les tests.
    mock_model_tasks = {
        key: MagicMock(kiq=AsyncMock()) for key in ("salesforce_blip", "florence2", "git_large")
    }
    mocker.patch("backend.worker.worker.MODEL_BATCH_TASKS", mock_model_tasks)

    return {
        "session": mock_session,
        "redis": mock_redis,
        "save_images": mock_save_images,
        "set_total": mock_set_total,
        "update": mock_update,
        "rmtree": mock_rmtree,
        "model_tasks": mock_model_tasks,
    }


class TestProcessEpubDescribe:
    """process_epub_describe est désormais un orchestrateur : il extrait les
    images, les sauvegarde (DB + MinIO) puis répartit ("fan-out") chaque
    (batch, modèle) sur la queue taskiq dédiée à ce modèle. Il n'appelle plus
    lui-même les modèles IA et ne bloque donc plus en attendant leur résultat.
    """

    @pytest.fixture(autouse=True)
    def _not_cancelled(self, mocker):
        """Par défaut, aucune tâche n'est annulée : is_cancelled() est mockée
        pour renvoyer False plutôt que de laisser tourner un MagicMock (qui
        serait toujours truthy et déclencherait le chemin d'annulation)."""
        return mocker.patch("backend.worker.worker.is_cancelled", return_value=False)

    class TestHappyPath:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_fans_out_one_kiq_per_batch_and_model(self, mocker):
            """Un batch de 2 images doit produire 2 * 3 (modèles) appels .kiq()."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            image_paths = ["/tmp/img1.png", "/tmp/img2.png"]
            temp_folder = "/tmp/epub_extract"
            fake_image_1 = MagicMock(id=101)
            fake_image_2 = MagicMock(id=102)
            fake_images = [fake_image_1, fake_image_2]

            mock_model_blip = MagicMock(name="Salesforce BLIP")
            mock_model_blip.name = "Salesforce BLIP"
            mock_model_blip.id = 1
            mock_model_florence = MagicMock(name="Florence-2")
            mock_model_florence.name = "Florence-2"
            mock_model_florence.id = 2
            mock_model_git = MagicMock(name="GIT Large")
            mock_model_git.name = "GIT Large"
            mock_model_git.id = 3

            mocks = _setup_process_epub_mocks(
                mocker,
                image_paths,
                temp_folder,
                fake_images,
                models=[mock_model_blip, mock_model_florence, mock_model_git],
            )
            mocker.patch.dict(os.environ, {"BATCH_SIZE": "2"})

            from backend.worker.worker import process_epub_describe

            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mocks["update"].assert_any_call(mocks["session"], db_task_id, "in_progress")
            mocks["save_images"].assert_called_once_with(
                mocks["session"], db_task_id, epub_id, image_paths
            )
            mocks["set_total"].assert_called_once_with(mocks["session"], db_task_id, 2)
            # Un seul batch (BATCH_SIZE=2, 2 images) : 1 appel par modèle.
            blip_kiq = mocks["model_tasks"]["salesforce_blip"].kiq
            florence_kiq = mocks["model_tasks"]["florence2"].kiq
            git_kiq = mocks["model_tasks"]["git_large"].kiq
            blip_kiq.assert_called_once()
            florence_kiq.assert_called_once()
            git_kiq.assert_called_once()

            call_args = blip_kiq.call_args.args
            assert call_args[0] == task_id
            assert call_args[1] == db_task_id
            assert call_args[2] == "salesforce_blip"
            assert call_args[3] == 1  # model_id résolu
            assert call_args[4] == "bucket"
            assert call_args[5] == [
                {"image_id": 101, "object_key": "key0"},
                {"image_id": 102, "object_key": "key1"},
            ]
            assert call_args[6] == 2  # total_images

            # Le dossier temporaire est nettoyé tout de suite après l'upload
            # MinIO, sans attendre les tâches modèles.
            mocks["rmtree"].assert_called_once_with(temp_folder)

            # La tâche n'est pas marquée "completed" par l'orchestrateur lui-même
            # (c'est la dernière tâche modèle qui finalise, cf. model_tasks.py).
            statuses = [c.args[2] for c in mocks["update"].call_args_list]
            assert "completed" not in statuses

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_images_marks_completed_immediately(self, mocker):
            """EPUB sans image : rien à répartir, la tâche est déjà terminée."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            mocks = _setup_process_epub_mocks(mocker, [], None, [])

            from backend.worker.worker import process_epub_describe

            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mocks["update"].assert_any_call(mocks["session"], db_task_id, "completed")
            for mock_task in mocks["model_tasks"].values():
                mock_task.kiq.assert_not_called()

            final_payload = json.loads(mocks["redis"].set.call_args_list[-1].args[1])
            assert final_payload["status"] == "completed"
            assert final_payload["total_images"] == 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_no_temp_folder_skips_cleanup(self, mocker):
            """Test que shutil.rmtree n'est pas appelé si temp_folder est None."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            image_paths = ["/tmp/img1.png"]
            fake_images = [MagicMock(id=1)]

            mocks = _setup_process_epub_mocks(mocker, image_paths, None, fake_images)

            from backend.worker.worker import process_epub_describe

            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mocks["rmtree"].assert_not_called()

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_cancelled_before_extraction_stops_early(self, mocker, _not_cancelled):
            """Si la tâche est déjà annulée, on ne fait ni extraction ni fan-out."""
            epub_path = "/path/to/book.epub"
            task_id = "redis-key-abc"
            db_task_id = 42
            epub_id = 7

            _not_cancelled.return_value = True
            mock_session = AsyncMock()
            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mocker.patch("backend.worker.worker.r")
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )
            mock_extract = mocker.patch("backend.worker.worker.extract_images_epub")

            from backend.worker.worker import process_epub_describe

            await process_epub_describe(epub_path, task_id, db_task_id, epub_id)

            mock_update.assert_any_call(mock_session, db_task_id, "cancelled")
            mock_extract.assert_not_called()

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
            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mocker.patch(
                "backend.worker.worker.extract_images_epub",
                side_effect=RuntimeError("Fichier corrompu"),
            )
            mocker.patch("backend.worker.worker.r")
            mock_update = mocker.patch(
                "backend.worker.worker.update_task_status", new_callable=AsyncMock
            )

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
            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mocker.patch(
                "backend.worker.worker.extract_images_epub", side_effect=RuntimeError(error_message)
            )
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
            mocker.patch(
                "backend.worker.worker.async_session",
                return_value=make_async_session_cm(mock_session),
            )
            mocker.patch(
                "backend.worker.worker.extract_images_epub",
                side_effect=ValueError("Erreur inattendue"),
            )
            mocker.patch("backend.worker.worker.r")
            mocker.patch("backend.worker.worker.update_task_status", new_callable=AsyncMock)

            from backend.worker.worker import process_epub_describe

            with pytest.raises(ValueError, match="Erreur inattendue"):
                await process_epub_describe(epub_path, task_id, db_task_id, epub_id)
