"""Tests d'intégration pour la récupération et validation des descriptions."""

import pytest
from datetime import datetime
from sqlalchemy import select

from backend.core.database.config import (
    Task,
    Epub,
    Images,
    DescriptionByIA,
    DescriptionFinale,
    ModelsIA,
    User,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _register_and_login(
    client, email: str, password: str = "TestPass123!", username: str = "descuser"
) -> str:
    """Inscrit un utilisateur et retourne son access_token (depuis le cookie httponly)."""
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.cookies.get("access_token")


async def _create_db_fixtures(session, user_id: int, task_id_redis: str) -> dict:
    """
    Crée directement en DB : Task, Epub, Images, ModelsIA, DescriptionByIA, DescriptionFinale.
    Retourne les objets créés.
    """
    # Task
    task = Task(
        task_id_redis=task_id_redis,
        user_id=user_id,
        status="completed",
        total_images=1,
        processed_images=1,
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )
    session.add(task)
    await session.flush()

    # Epub
    epub = Epub(
        task_id=task.id,
        file_name=f"desc_test_{task_id_redis}.epub",
        upload_date=datetime.now(),
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(epub)
    await session.flush()

    # Image
    image = Images(
        task_id=task.id,
        epub_id=epub.id,
        image_file_name="test_image.jpg",
        image_position_in_epub=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(image)
    await session.flush()

    # Modèles IA
    model_salesforce = ModelsIA(
        name="Salesforce BLIP",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    model_florence = ModelsIA(
        name="Florence-2",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    model_git = ModelsIA(
        name="GIT Large",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add_all([model_salesforce, model_florence, model_git])
    await session.flush()

    # Descriptions IA (3 modèles)
    for model, text in [
        (model_salesforce, "Description Salesforce BLIP"),
        (model_florence, "Description Florence-2"),
        (model_git, "Description GIT Large"),
    ]:
        desc = DescriptionByIA(
            image_id=image.id,
            model_ia_id=model.id,
            description_text=text,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(desc)

    # Description finale (validée par l'humain — modèle Salesforce choisi)
    final = DescriptionFinale(
        user_id=user_id,
        image_id=image.id,
        model_ia_id=model_salesforce.id,
        description_text="Description Salesforce BLIP",
        validated_by_human=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(final)

    await session.commit()

    return {
        "task": task,
        "epub": epub,
        "image": image,
        "models": {
            "salesforce_blip": model_salesforce,
            "florence2": model_florence,
            "git_large": model_git,
        },
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
class TestDescriptionIntegration:
    async def test_get_descriptions_for_task(self, client, async_session):
        """GET /api/description/{task_id} retourne les descriptions pour une tâche existante."""
        reg = _register_and_login(client, "desc_get@example.com")
        token = reg
        # Récupérer le user_id depuis la DB
        result = await async_session.execute(
            select(User).where(User.email == "desc_get@example.com")
        )
        user = result.scalars().first()
        assert user is not None

        task_id_redis = "desc-test-task-001"
        await _create_db_fixtures(async_session, user.id, task_id_redis)

        response = client.get(
            f"/api/description/{task_id_redis}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["task_id"] == task_id_redis
        assert "images" in body
        assert len(body["images"]) == 1

    async def test_get_descriptions_nonexistent_task_returns_404(self, client):
        """GET /api/description/{task_id} avec un task_id inexistant retourne 404."""
        reg = _register_and_login(client, "desc_404@example.com")
        token = reg
        response = client.get(
            "/api/description/nonexistent-task-id-99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, response.text

    async def test_descriptions_contain_expected_fields(self, client, async_session):
        """Les descriptions retournées contiennent les champs attendus par image."""
        reg = _register_and_login(client, "desc_fields@example.com")
        token = reg
        result = await async_session.execute(
            select(User).where(User.email == "desc_fields@example.com")
        )
        user = result.scalars().first()

        task_id_redis = "desc-fields-task-002"
        await _create_db_fixtures(async_session, user.id, task_id_redis)

        response = client.get(
            f"/api/description/{task_id_redis}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        images = body["images"]
        assert len(images) > 0

        image_data = images[0]
        assert "image_id" in image_data
        assert "image_file_name" in image_data
        assert "image_position_in_epub" in image_data
        assert "descriptions" in image_data

        descs = image_data["descriptions"]
        assert len(descs) == 3

        model_keys = {d["model_key"] for d in descs}
        assert "salesforce_blip" in model_keys
        assert "florence2" in model_keys
        assert "git_large" in model_keys

        for desc in descs:
            assert "description_id" in desc
            assert "description_text" in desc
            assert "model_name" in desc
            assert "model_key" in desc

    async def test_get_descriptions_task_belonging_to_other_user_returns_404(
        self, client, async_session
    ):
        """Un utilisateur ne peut pas voir les descriptions d'une tâche appartenant à un autre (404)."""
        # Créer le propriétaire et sa tâche
        result = await async_session.execute(
            select(User).where(User.email == "desc_owner@example.com")
        )
        owner = result.scalars().first()

        task_id_redis = "desc-owner-task-003"
        await _create_db_fixtures(async_session, owner.id, task_id_redis)

        # L'intrus tente d'accéder aux descriptions
        reg_intruder = _register_and_login(
            client, "desc_intruder@example.com", username="descintruder"
        )
        token_intruder = reg_intruder
        response = client.get(
            f"/api/description/{task_id_redis}",
            headers={"Authorization": f"Bearer {token_intruder}"},
        )
        assert response.status_code == 404, response.text

    async def test_get_descriptions_without_token_returns_401(self, client):
        """GET /api/description/{task_id} sans token retourne 401."""
        response = client.get("/api/description/any-task-id")
        assert response.status_code == 401, response.text

    async def test_descriptions_status_reflects_task(self, client, async_session):
        """Le champ 'status' dans la réponse correspond au statut de la tâche en DB."""
        reg = _register_and_login(client, "desc_status@example.com")
        token = reg
        result = await async_session.execute(
            select(User).where(User.email == "desc_status@example.com")
        )
        user = result.scalars().first()

        task_id_redis = "desc-status-task-004"
        await _create_db_fixtures(async_session, user.id, task_id_redis)

        response = client.get(
            f"/api/description/{task_id_redis}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "completed"
        assert body["total_images"] == 1

    async def test_validate_descriptions_success(self, client, async_session):
        """POST /api/description/{task_id}/validate valide les descriptions AI → 200."""
        reg = _register_and_login(client, "desc_validate@example.com", username="descvalidate")
        token = reg
        result = await async_session.execute(
            select(User).where(User.email == "desc_validate@example.com")
        )
        user = result.scalars().first()

        task_id_redis = "desc-validate-task-005"
        await _create_db_fixtures(async_session, user.id, task_id_redis)

        payload = {
            "validated_descriptions": [
                {
                    "image_index": 0,
                    "text": "Description Salesforce BLIP",
                    "model": "salesforce_blip",
                }
            ]
        }

        response = client.post(
            f"/api/description/{task_id_redis}/validate",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True

    async def test_validate_descriptions_nonexistent_task_returns_404(self, client):
        """POST /api/description/{task_id}/validate avec tâche inexistante → 404."""
        reg = _register_and_login(client, "desc_val_404@example.com", username="descval404")
        token = reg
        payload = {"validated_descriptions": []}

        response = client.post(
            "/api/description/nonexistent-task-val-99999/validate",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404, response.text

    async def test_validate_descriptions_without_token_returns_401(self, client):
        """POST /api/description/{task_id}/validate sans token → 401."""
        payload = {"validated_descriptions": []}

        response = client.post(
            "/api/description/any-task-id/validate",
            json=payload,
        )
        assert response.status_code == 401, response.text

    async def test_validate_descriptions_other_user_task_returns_404(self, client, async_session):
        """Un utilisateur ne peut pas valider les descriptions d'une tâche d'un autre → 404."""
        result = await async_session.execute(
            select(User).where(User.email == "desc_val_owner@example.com")
        )
        owner = result.scalars().first()

        task_id_redis = "desc-val-owner-task-006"
        await _create_db_fixtures(async_session, owner.id, task_id_redis)

        reg_intruder = _register_and_login(
            client, "desc_val_intruder@example.com", username="descvalintruder"
        )
        token_intruder = reg_intruder
        payload = {"validated_descriptions": []}
        response = client.post(
            f"/api/description/{task_id_redis}/validate",
            json=payload,
            headers={"Authorization": f"Bearer {token_intruder}"},
        )
        assert response.status_code == 404, response.text
