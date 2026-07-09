"""Tests d'intégration pour la gestion des tâches."""

import io
import pytest
from sqlalchemy import select

from backend.core.database.config import Epub, Task


# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_minimal_epub() -> bytes:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("task-test-id")
    book.set_title("Task Test Book")
    book.set_language("fr")
    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _register_and_login(
    client, email: str, password: str = "TestPass123!", username: str = "taskuser"
) -> str:
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    return resp.cookies.get("access_token")


def _upload_epub(client, token: str, epub_bytes: bytes, filename: str = "task_test.epub"):
    return client.post(
        "/api/epub/upload-epub",
        files={"upload": (filename, io.BytesIO(epub_bytes), "application/epub+zip")},
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskIntegration:
    async def test_create_task_saves_to_db(self, client, async_session):
        """Uploader un EPUB crée une tâche en DB avec le bon user_id et les valeurs initiales."""
        token = _register_and_login(client, "task_create_db@example.com")
        epub_bytes = _create_minimal_epub()

        response = _upload_epub(client, token, epub_bytes, "task_create.epub")
        assert response.status_code in (200, 201), response.text

        task_id = response.json()["task_id"]

        result = await async_session.execute(select(Task).where(Task.task_id_redis == task_id))
        task = result.scalars().first()
        assert task is not None
        assert task.task_id_redis == task_id
        assert task.status == "pending"
        assert task.user_id is not None
        assert task.total_images == 0
        assert task.processed_images == 0

    async def test_get_task_status_returns_correct_status(self, client, async_session):
        """GET /api/task/{task_id} retourne les données de la tâche (202 si en attente)."""
        token = _register_and_login(client, "task_status@example.com")
        epub_bytes = _create_minimal_epub()

        upload_resp = _upload_epub(client, token, epub_bytes, "task_status.epub")
        assert upload_resp.status_code in (200, 201), upload_resp.text
        task_id = upload_resp.json()["task_id"]

        # La tâche vient d'être créée — Redis contient {"status": "en attente", ...}
        response = client.get(
            f"/api/task/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 202 = en attente, 200 = résultat dispo
        assert response.status_code in (200, 202), response.text

    async def test_get_nonexistent_task_returns_404(self, client):
        """GET /api/task/{task_id} avec un task_id inexistant retourne 404."""
        token = _register_and_login(client, "task_404@example.com")

        response = client.get(
            "/api/task/nonexistent-task-id-000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, response.text

    async def test_task_belongs_to_user(self, client, async_session):
        """Un utilisateur ne peut pas accéder à la tâche d'un autre (403)."""
        # User 1 crée une tâche
        token1 = _register_and_login(client, "task_owner@example.com", username="owner")
        epub_bytes = _create_minimal_epub()
        upload_resp = _upload_epub(client, token1, epub_bytes, "owner_task.epub")
        assert upload_resp.status_code in (200, 201), upload_resp.text
        task_id = upload_resp.json()["task_id"]

        # User 2 tente d'y accéder
        token2 = _register_and_login(client, "task_intruder@example.com", username="intruder")
        response = client.get(
            f"/api/task/{task_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code in (403, 404), response.text

    async def test_get_task_without_token_returns_401(self, client):
        """GET /api/task/{task_id} sans token retourne 401."""
        response = client.get("/api/task/some-task-id")
        assert response.status_code == 401, response.text

    async def test_get_all_tasks_as_non_admin_returns_403(self, client):
        """GET /api/task/admin par un utilisateur normal retourne 403."""
        token = _register_and_login(client, "task_nonadmin@example.com", username="nonadmin")

        response = client.get(
            "/api/task/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, response.text


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskCancellation:
    """POST /api/task/{task_id}/cancel : annulation + suppression de l'epub
    pour permettre de relancer un traitement sur le même fichier."""

    async def test_cancel_pending_task_marks_cancelled_and_deletes_epub(
        self, client, async_session
    ):
        token = _register_and_login(client, "cancel_basic@example.com", username="cancelbasic")
        epub_bytes = _create_minimal_epub()
        upload_resp = _upload_epub(client, token, epub_bytes, "cancel_basic.epub")
        assert upload_resp.status_code in (200, 201), upload_resp.text
        task_id = upload_resp.json()["task_id"]

        response = client.post(
            f"/api/task/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"task_id": task_id, "status": "cancelled"}

        result = await async_session.execute(select(Task).where(Task.task_id_redis == task_id))
        task = result.scalars().first()
        assert task.status == "cancelled"

        epub_result = await async_session.execute(
            select(Epub).where(Epub.task_id == task.id)
        )
        assert epub_result.scalars().first() is None

    async def test_cancel_allows_reupload_of_same_filename(self, client):
        token = _register_and_login(client, "cancel_reupload@example.com", username="cancelre")
        epub_bytes = _create_minimal_epub()
        filename = "cancel_reupload.epub"

        first_upload = _upload_epub(client, token, epub_bytes, filename)
        assert first_upload.status_code in (200, 201), first_upload.text
        task_id = first_upload.json()["task_id"]

        cancel_resp = client.post(
            f"/api/task/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_resp.status_code == 200, cancel_resp.text

        second_upload = _upload_epub(client, token, epub_bytes, filename)
        assert second_upload.status_code in (200, 201), second_upload.text
        assert second_upload.json()["task_id"] != task_id

    async def test_cancel_wrong_owner_returns_403(self, client):
        token_owner = _register_and_login(client, "cancel_owner@example.com", username="cancelowner")
        epub_bytes = _create_minimal_epub()
        upload_resp = _upload_epub(client, token_owner, epub_bytes, "cancel_owner.epub")
        assert upload_resp.status_code in (200, 201), upload_resp.text
        task_id = upload_resp.json()["task_id"]

        token_intruder = _register_and_login(
            client, "cancel_intruder@example.com", username="cancelintruder"
        )
        response = client.post(
            f"/api/task/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token_intruder}"},
        )
        assert response.status_code == 403, response.text

    async def test_cancel_nonexistent_task_returns_404(self, client):
        token = _register_and_login(client, "cancel_404@example.com", username="cancel404")

        response = client.post(
            "/api/task/nonexistent-task-id-000000/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, response.text

    async def test_cancel_already_cancelled_returns_409(self, client):
        token = _register_and_login(client, "cancel_twice@example.com", username="canceltwice")
        epub_bytes = _create_minimal_epub()
        upload_resp = _upload_epub(client, token, epub_bytes, "cancel_twice.epub")
        assert upload_resp.status_code in (200, 201), upload_resp.text
        task_id = upload_resp.json()["task_id"]

        first_cancel = client.post(
            f"/api/task/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first_cancel.status_code == 200, first_cancel.text

        second_cancel = client.post(
            f"/api/task/{task_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second_cancel.status_code == 409, second_cancel.text

    async def test_cancel_without_token_returns_401(self, client):
        response = client.post("/api/task/some-task-id/cancel")
        assert response.status_code == 401, response.text
