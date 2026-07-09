import json
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock


class TestGetTaskResult:
    """Tests des branches de polling de get_task_result (pending/in_progress/completed)."""

    def _setup(self, mocker, redis_payload):
        from backend.tasks import controller

        task = MagicMock()
        task.user_id = 1
        mocker.patch.object(
            controller, "find_task_by_redis_id", new=AsyncMock(return_value=task)
        )
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(redis_payload).encode("utf-8")
        mocker.patch.object(controller, "redis_dev", mock_redis)
        return controller

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pending_returns_202(self, mocker):
        controller = self._setup(mocker, {"status": "en attente", "epub_path": "/x"})
        current_user = MagicMock(id=1)

        resp = await controller.get_task_result("t1", current_user, db=MagicMock())

        assert resp.status_code == 202
        body = json.loads(resp.body)
        assert body["completed"] is False
        assert body["status"] == "pending"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_in_progress_returns_partial(self, mocker):
        """processed_images vient du compteur Redis atomique, le contenu des
        descriptions de la DB (via build_task_progress_payload) : il n'y a
        plus de blob Redis agrégé à jour en continu depuis le passage en
        multi-queue (chaque tâche modèle persiste directement en DB)."""
        payload = {"status": "in_progress", "total_images": 4}
        controller = self._setup(mocker, payload)
        progress_payload = {"images": {"image_0": {}}, "total_images": 4}
        mocker.patch.object(
            controller,
            "build_task_progress_payload",
            new=AsyncMock(return_value=progress_payload),
        )
        controller.redis_dev.get.side_effect = lambda key: (
            json.dumps(payload).encode("utf-8") if key == "t1" else b"2"
        )
        current_user = MagicMock(id=1)

        resp = await controller.get_task_result("t1", current_user, db=MagicMock())

        assert resp["completed"] is False
        assert resp["status"] == "in_progress"
        assert resp["total_images"] == 4
        assert resp["processed_images"] == 2
        assert resp["result"] == progress_payload

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_completed_returns_final(self, mocker):
        payload = {"status": "completed", "total_images": 1}
        controller = self._setup(mocker, payload)
        progress_payload = {"images": {}, "total_images": 1}
        mocker.patch.object(
            controller,
            "build_task_progress_payload",
            new=AsyncMock(return_value=progress_payload),
        )
        current_user = MagicMock(id=1)

        resp = await controller.get_task_result("t1", current_user, db=MagicMock())

        assert resp["completed"] is True
        assert resp["status"] == "completed"
        assert resp["result"] == progress_payload

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_legacy_payload_without_status_returns_final(self, mocker):
        payload = {"epub_path": "/x", "descriptions": {"images": {}}}
        controller = self._setup(mocker, payload)
        current_user = MagicMock(id=1)

        resp = await controller.get_task_result("t1", current_user, db=MagicMock())

        assert resp["completed"] is True
        assert resp["result"] == payload


class TestCancelTaskEndpoint:
    """Tests du controller cancel_task (POST /api/task/{task_id}/cancel)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, mocker):
        from backend.tasks import controller

        mocker.patch.object(controller, "find_task_by_redis_id", new=AsyncMock(return_value=None))
        current_user = MagicMock(id=1)

        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_task("t1", current_user, db=MagicMock())
        assert exc_info.value.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wrong_owner_returns_403(self, mocker):
        from backend.tasks import controller

        task = MagicMock(user_id=2, status="pending")
        mocker.patch.object(controller, "find_task_by_redis_id", new=AsyncMock(return_value=task))
        current_user = MagicMock(id=1)

        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_task("t1", current_user, db=MagicMock())
        assert exc_info.value.status_code == 403

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_value", ["completed", "failed", "cancelled"])
    async def test_already_terminal_returns_409(self, mocker, status_value):
        from backend.tasks import controller

        task = MagicMock(user_id=1, status=status_value)
        mocker.patch.object(controller, "find_task_by_redis_id", new=AsyncMock(return_value=task))
        current_user = MagicMock(id=1)

        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_task("t1", current_user, db=MagicMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_value", ["pending", "in_progress"])
    async def test_cancellable_status_calls_service_and_returns_payload(self, mocker, status_value):
        from backend.tasks import controller

        task = MagicMock(user_id=1, status=status_value)
        mocker.patch.object(controller, "find_task_by_redis_id", new=AsyncMock(return_value=task))
        mock_cancel = mocker.patch.object(
            controller, "_cancel_task_processing", new=AsyncMock()
        )
        current_user = MagicMock(id=1)
        db = MagicMock()

        result = await controller.cancel_task("t1", current_user, db=db)

        mock_cancel.assert_called_once_with(db, controller.redis_dev, task)
        assert result == {"task_id": "t1", "status": "cancelled"}


class TestCancelTaskService:
    """Tests du service cancel_task : annulation Redis + suppression Epub/MinIO/fichier."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancels_deletes_epub_and_cleans_storage(self, mocker, session):
        from backend.tasks import service

        task = MagicMock(id=5, task_id_redis="task-1")
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"epub_path": "/shared/book.epub"}).encode()

        mock_mark_cancelled = mocker.patch.object(service, "mark_cancelled")
        mock_update = mocker.patch.object(service, "_update_task_status", new=AsyncMock())
        mock_delete = mocker.patch.object(
            service,
            "delete_epub_and_children",
            new=AsyncMock(return_value=[("bucket", "key1"), ("bucket", "key2")]),
        )
        mock_remove_objects = mocker.patch.object(service, "remove_objects")
        mocker.patch("os.path.exists", return_value=True)
        mock_remove = mocker.patch("os.remove")

        await service.cancel_task(session, mock_redis, task)

        mock_mark_cancelled.assert_called_once_with(mock_redis, "task-1")
        mock_update.assert_called_once_with(session, 5, "cancelled")
        mock_delete.assert_called_once_with(session, 5)
        mock_remove_objects.assert_called_once_with("bucket", ["key1", "key2"])
        mock_remove.assert_called_once_with("/shared/book.epub")
        final_payload = json.loads(mock_redis.set.call_args.args[1])
        assert final_payload["status"] == "cancelled"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_epub_file_on_disk_is_ignored(self, mocker, session):
        from backend.tasks import service

        task = MagicMock(id=5, task_id_redis="task-1")
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"epub_path": "/shared/book.epub"}).encode()

        mocker.patch.object(service, "mark_cancelled")
        mocker.patch.object(service, "_update_task_status", new=AsyncMock())
        mocker.patch.object(service, "delete_epub_and_children", new=AsyncMock(return_value=[]))
        mocker.patch.object(service, "remove_objects")
        mocker.patch("os.path.exists", return_value=False)
        mock_remove = mocker.patch("os.remove")

        await service.cancel_task(session, mock_redis, task)

        mock_remove.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_redis_payload_skips_file_deletion(self, mocker, session):
        from backend.tasks import service

        task = MagicMock(id=5, task_id_redis="task-1")
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        mocker.patch.object(service, "mark_cancelled")
        mocker.patch.object(service, "_update_task_status", new=AsyncMock())
        mocker.patch.object(service, "delete_epub_and_children", new=AsyncMock(return_value=[]))
        mocker.patch.object(service, "remove_objects")
        mock_exists = mocker.patch("os.path.exists")

        await service.cancel_task(session, mock_redis, task)

        mock_exists.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_storage_locations_skips_remove_objects(self, mocker, session):
        from backend.tasks import service

        task = MagicMock(id=5, task_id_redis="task-1")
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        mocker.patch.object(service, "mark_cancelled")
        mocker.patch.object(service, "_update_task_status", new=AsyncMock())
        mocker.patch.object(service, "delete_epub_and_children", new=AsyncMock(return_value=[]))
        mock_remove_objects = mocker.patch.object(service, "remove_objects")

        await service.cancel_task(session, mock_redis, task)

        mock_remove_objects.assert_not_called()


class TestTaskService:
    class TestGetModelKey:
        @pytest.mark.unit
        @pytest.mark.parametrize(
            "db_name, expected",
            [
                ("Salesforce BLIP", "salesforce_blip"),
                ("Florence-2", "florence2"),
                ("GIT Large", "git_large"),
                (None, None),
                ("unknown_model", "unknown_model"),
            ],
        )
        def test_get_model_key(self, db_name, expected):
            """Mappe le nom réel d'un modèle en DB vers sa clé interne (None et nom inconnu inclus)."""
            from backend.tasks.service import _get_model_key

            assert _get_model_key(db_name) == expected

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
            """Une description écrite à la main (model=None) crée une nouvelle DescriptionFinale."""
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.user_id = 42

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

            # upsert_final_description appelle find_final_description_by_image :
            # on simule l'absence de description existante pour forcer la création.
            mock_existing_result = MagicMock()
            mock_existing_result.scalar_one_or_none.return_value = None

            session.execute = AsyncMock(
                side_effect=[
                    mock_task_result,
                    mock_images_result,
                    mock_models_result,
                    mock_existing_result,
                ]
            )

            desc_data = MagicMock()
            desc_data.image_index = 0
            desc_data.model = None
            desc_data.text = "Description écrite par un humain"

            from backend.tasks.service import validate_task_descriptions

            result = await validate_task_descriptions(
                session=session, task_id_redis="task-abc", descriptions=[desc_data]
            )

            assert result is True
            session.add.assert_called_once()
            session.commit.assert_called_once()

            added_desc = session.add.call_args[0][0]
            assert added_desc.image_id == 5
            assert added_desc.user_id == 42
            assert added_desc.model_ia_id is None
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
