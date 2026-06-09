"""Tests d'intégration pour l'upload et la gestion des EPUBs."""

import io
import pytest
from sqlalchemy import select

from backend.core.database.config import Epub, Task


# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_minimal_epub(filename: str = "test.epub") -> bytes:
    """Crée un EPUB minimal valide en mémoire via ebooklib."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-id-001")
    book.set_title("Test Book")
    book.set_language("fr")

    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _register_and_login(client, email: str, password: str = "TestPass123!") -> str:
    """Inscrit un utilisateur et retourne son access_token (depuis le cookie httponly)."""
    resp = client.post(
        "/api/auth/register",
        json={"username": "epubuser", "email": email, "password": password},
    )
    return resp.cookies.get("access_token")


def _upload_epub(client, token: str, epub_bytes: bytes, filename: str = "test.epub"):
    return client.post(
        "/api/epub/upload-epub",
        files={"upload": (filename, io.BytesIO(epub_bytes), "application/epub+zip")},
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
class TestEpubIntegration:
    async def test_upload_epub_saves_to_db(self, client, async_session):
        """L'upload d'un EPUB crée bien une entrée Task et Epub en base."""
        token = _register_and_login(client, "epub_upload_db@example.com")
        epub_bytes = _create_minimal_epub()

        response = _upload_epub(client, token, epub_bytes, "book_db.epub")

        assert response.status_code in (200, 201), response.text
        body = response.json()
        assert "task_id" in body

        # Vérifier la présence en DB
        result = await async_session.execute(select(Epub).where(Epub.file_name == "book_db.epub"))
        epub_record = result.scalars().first()
        assert epub_record is not None
        assert epub_record.file_name == "book_db.epub"

    async def test_upload_epub_creates_task_in_db(self, client, async_session):
        """L'upload d'un EPUB crée une tâche en base avec le bon task_id_redis."""
        token = _register_and_login(client, "epub_task_db@example.com")
        epub_bytes = _create_minimal_epub()

        response = _upload_epub(client, token, epub_bytes, "book_task.epub")

        assert response.status_code in (200, 201), response.text
        task_id = response.json()["task_id"]

        result = await async_session.execute(select(Task).where(Task.task_id_redis == task_id))
        task_record = result.scalars().first()
        assert task_record is not None
        assert task_record.task_id_redis == task_id
        assert task_record.status == "pending"

    async def test_upload_same_epub_twice_returns_conflict(self, client):
        """Uploader deux fois le même fichier (même nom) retourne 409."""
        token = _register_and_login(client, "epub_conflict@example.com")
        epub_bytes = _create_minimal_epub()
        filename = "duplicate_book.epub"

        r1 = _upload_epub(client, token, epub_bytes, filename)
        assert r1.status_code in (200, 201), r1.text

        r2 = _upload_epub(client, token, epub_bytes, filename)
        assert r2.status_code == 409, r2.text

    async def test_upload_non_epub_file_returns_error(self, client):
        """Uploader un fichier non .epub retourne 400."""
        token = _register_and_login(client, "epub_invalid_ext@example.com")
        fake_content = b"This is not an epub file"

        response = client.post(
            "/api/epub/upload-epub",
            files={"upload": ("document.txt", io.BytesIO(fake_content), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400, response.text

    async def test_upload_epub_without_token_returns_401(self, client):
        """Uploader un EPUB sans token retourne 401."""
        epub_bytes = _create_minimal_epub()

        response = client.post(
            "/api/epub/upload-epub",
            files={"upload": ("noauth.epub", io.BytesIO(epub_bytes), "application/epub+zip")},
        )
        assert response.status_code == 401, response.text

    async def test_upload_pdf_file_returns_error(self, client):
        """Uploader un fichier .pdf (pas .epub) retourne 400."""
        token = _register_and_login(client, "epub_pdf_ext@example.com")
        fake_pdf = b"%PDF-1.4 fake pdf content"

        response = client.post(
            "/api/epub/upload-epub",
            files={"upload": ("document.pdf", io.BytesIO(fake_pdf), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400, response.text

    async def test_download_epub_not_found_returns_404(self, client):
        """Télécharger un fichier inexistant retourne 404."""
        token = _register_and_login(client, "epub_download_404@example.com")

        response = client.get(
            "/api/epub/download-epub/fichier_inexistant.epub",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, response.text

    async def test_download_epub_without_token_returns_401(self, client):
        """Télécharger un fichier sans token retourne 401."""
        response = client.get("/api/epub/download-epub/test.epub")
        assert response.status_code == 401, response.text
