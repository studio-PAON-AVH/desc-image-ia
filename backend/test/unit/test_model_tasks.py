import pytest
from unittest.mock import AsyncMock, MagicMock


def make_async_session_cm(session_mock):
    """Crée un context manager async simulant async_session()."""
    cm = AsyncMock()
    cm.__aenter__.return_value = session_mock
    cm.__aexit__.return_value = None
    return cm


class TestDescribeBatch:
    """_describe_batch est l'implémentation commune aux 3 tâches par modèle :
    télécharge les images du batch depuis MinIO, appelle le modèle, persiste
    le résultat, incrémente la progression et finalise la tâche si c'est le
    dernier batch en attente."""

    def _patch_common(self, mocker, cancelled=False):
        mocker.patch("backend.worker.model_tasks.is_cancelled", return_value=cancelled)
        mock_redis = mocker.patch("backend.worker.model_tasks.r")
        mock_download = mocker.patch(
            "backend.worker.model_tasks.download_object_bytes", return_value=b"raw-bytes"
        )
        mock_call_model = mocker.patch(
            "backend.worker.model_tasks.call_model",
            new_callable=AsyncMock,
            return_value={"results": [{"french_description": "Un chat"}]},
        )
        mocker.patch("backend.worker.model_tasks.get_model_url", return_value="http://model/describe")
        mock_persist = mocker.patch(
            "backend.worker.model_tasks.save_descriptions_by_ids", new_callable=AsyncMock
        )
        mock_session = AsyncMock()
        mocker.patch(
            "backend.worker.model_tasks.async_session",
            return_value=make_async_session_cm(mock_session),
        )
        mock_update = mocker.patch(
            "backend.worker.model_tasks._repo_update_task_status", new_callable=AsyncMock
        )
        mock_task_counter = mocker.patch("backend.worker.model_tasks.task_counter")
        mock_task_duration = mocker.patch("backend.worker.model_tasks.task_duration")
        return {
            "redis": mock_redis,
            "download": mock_download,
            "call_model": mock_call_model,
            "persist": mock_persist,
            "session": mock_session,
            "update": mock_update,
            "task_counter": mock_task_counter,
            "task_duration": mock_task_duration,
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancelled_before_start_skips_everything(self, mocker):
        mocks = self._patch_common(mocker, cancelled=True)

        from backend.worker.model_tasks import _describe_batch

        await _describe_batch(
            "task-1", 1, "salesforce_blip", 10, "bucket", [{"image_id": 1, "object_key": "k1"}], 1
        )

        mocks["download"].assert_not_called()
        mocks["call_model"].assert_not_called()
        mocks["persist"].assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_persists_and_increments_counters(self, mocker):
        mocks = self._patch_common(mocker, cancelled=False)
        mocks["redis"].incr.return_value = 1  # pas encore le dernier modèle pour cette image
        mocks["redis"].decr.return_value = 2  # d'autres batches restent en attente

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mocks["download"].assert_called_once_with("bucket", "key0")
        mocks["call_model"].assert_called_once()
        mocks["persist"].assert_called_once_with(mocks["session"], 7, [(101, "Un chat")])
        # Pas le dernier modèle à traiter cette image -> pas d'incrément du
        # compteur global d'images traitées.
        assert mocks["redis"].incr.call_count == 1
        # Toujours pas le dernier batch -> pas de finalisation.
        mocks["update"].assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_last_model_for_image_increments_processed_counter(self, mocker):
        mocks = self._patch_common(mocker, cancelled=False)
        mocks["redis"].incr.return_value = 3  # les 3 modèles ont fini cette image
        mocks["redis"].decr.return_value = 1

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "git_large", 3, "bucket", batch_images, 1)

        # image_done atteint NUM_MODELS -> incrément du compteur processed en plus.
        assert mocks["redis"].incr.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_last_batch_finalizes_task_as_completed(self, mocker):
        mocks = self._patch_common(mocker, cancelled=False)
        mocks["redis"].incr.return_value = 1
        mocks["redis"].decr.return_value = 0  # dernier batch en attente
        mocks["redis"].get.return_value = b"100.0"

        mock_task = MagicMock(status="in_progress")
        mocks["session"].get = AsyncMock(return_value=mock_task)

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mocks["update"].assert_called_once_with(mocks["session"], 42, "completed")
        mocks["task_counter"].add.assert_called_once_with(1, {"status": "completed"})
        final_set_call = mocks["redis"].set.call_args_list[-1]
        assert final_set_call.args[0] == "task-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_last_batch_does_not_override_already_failed_or_cancelled(self, mocker):
        """Si une autre tâche a déjà marqué le statut != in_progress (échec ou
        annulation concurrente), le dernier décrément ne doit pas écraser ce
        statut avec "completed"."""
        mocks = self._patch_common(mocker, cancelled=False)
        mocks["redis"].incr.return_value = 1
        mocks["redis"].decr.return_value = 0

        mock_task = MagicMock(status="failed")
        mocks["session"].get = AsyncMock(return_value=mock_task)

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mocks["update"].assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancelled_after_model_call_skips_persist(self, mocker):
        mocker.patch("backend.worker.model_tasks.download_object_bytes", return_value=b"raw")
        mocker.patch(
            "backend.worker.model_tasks.call_model",
            new_callable=AsyncMock,
            return_value={"results": [{"french_description": "x"}]},
        )
        mocker.patch("backend.worker.model_tasks.get_model_url", return_value="http://model")
        mock_persist = mocker.patch(
            "backend.worker.model_tasks.save_descriptions_by_ids", new_callable=AsyncMock
        )
        mocker.patch("backend.worker.model_tasks.r")
        # Pas annulée au tout début, mais annulée juste après l'appel modèle.
        mocker.patch("backend.worker.model_tasks.is_cancelled", side_effect=[False, True])

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mock_persist.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_marks_task_failed(self, mocker):
        mocks = self._patch_common(mocker, cancelled=False)
        mocks["download"].side_effect = RuntimeError("MinIO indisponible")

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mocks["update"].assert_called_once_with(mocks["session"], 42, "failed")
        mocks["task_counter"].add.assert_called_once_with(1, {"status": "failed"})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_while_cancelled_does_not_mark_failed(self, mocker):
        """Une exception survenant après une annulation concurrente (par ex.
        l'image a déjà été supprimée de MinIO par le endpoint d'annulation) ne
        doit pas écraser le statut "cancelled" avec "failed"."""
        mock_redis = mocker.patch("backend.worker.model_tasks.r")
        # Pas encore annulée au tout début (on passe la garde initiale), mais
        # annulée au moment où l'exception est traitée dans le except.
        mocker.patch("backend.worker.model_tasks.is_cancelled", side_effect=[False, True])
        mock_download = mocker.patch(
            "backend.worker.model_tasks.download_object_bytes",
            side_effect=RuntimeError("objet déjà supprimé"),
        )
        mock_update = mocker.patch(
            "backend.worker.model_tasks._repo_update_task_status", new_callable=AsyncMock
        )

        from backend.worker.model_tasks import _describe_batch

        batch_images = [{"image_id": 101, "object_key": "key0"}]
        await _describe_batch("task-1", 42, "salesforce_blip", 7, "bucket", batch_images, 1)

        mock_download.assert_called_once()
        mock_update.assert_not_called()
        mock_redis.set.assert_not_called()
