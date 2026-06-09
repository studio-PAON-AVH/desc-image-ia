"""Tests d'intégration pour l'authentification."""

import pytest
from sqlalchemy import select

from backend.core.database.config import User


# ── Helpers ───────────────────────────────────────────────────────────────────


def _register(client, email: str, password: str = "TestPass123!", username: str = "testuser"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def _login(client, email: str, password: str = "TestPass123!"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthIntegration:
    async def test_register_creates_user_in_db(self, client, async_session):
        """L'inscription crée bien l'utilisateur en base de données."""
        email = "register_db@example.com"
        response = _register(client, email)

        assert response.status_code in (200, 201), response.text

        result = await async_session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        assert user is not None
        assert user.email == email

    async def test_register_returns_tokens(self, client):
        """L'inscription set un access_token et un refresh_token en cookie."""
        response = _register(client, "register_tokens@example.com")

        assert response.status_code in (200, 201), response.text
        assert response.cookies.get("access_token") is not None
        assert response.cookies.get("refresh_token") is not None

    async def test_register_duplicate_email_returns_conflict(self, client):
        """Enregistrer deux fois le même email retourne 409."""
        email = "duplicate@example.com"
        r1 = _register(client, email)
        assert r1.status_code in (200, 201), r1.text

        r2 = _register(client, email)
        assert r2.status_code == 409, r2.text

    async def test_login_returns_jwt_token(self, client):
        """Après inscription, le login set un access_token en cookie."""
        email = "login_jwt@example.com"
        password = "TestPass123!"
        _register(client, email, password)

        response = _login(client, email, password)

        assert response.status_code == 200, response.text
        assert response.cookies.get("access_token") is not None
        assert response.json()["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client):
        """Un mauvais mot de passe lors du login retourne 401."""
        email = "wrong_pass@example.com"
        _register(client, email, "CorrectPass123!")

        response = _login(client, email, "WrongPassword!")

        assert response.status_code == 401, response.text

    async def test_protected_route_without_token_returns_401(self, client):
        """Accéder à une route protégée sans token retourne 401."""
        response = client.get("/api/auth/users/me")
        assert response.status_code == 401, response.text

    async def test_protected_route_with_valid_token_succeeds(self, client):
        """Avec un token valide, une route protégée répond (pas 401)."""
        email = "protected_valid@example.com"
        reg = _register(client, email)
        token = reg.cookies.get("access_token")

        response = client.get(
            "/api/auth/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code not in (401, 403), response.text
        body = response.json()
        assert body["email"] == email

    async def test_get_user_tasks_returns_empty_list_initially(self, client):
        """Après inscription, la liste des tâches de l'utilisateur est vide."""
        email = "tasks_empty@example.com"
        reg = _register(client, email)
        token = reg.cookies.get("access_token")

        response = client.get(
            "/api/auth/users/me/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "tasks" in body
        assert body["tasks"] == []

    async def test_refresh_token_returns_new_tokens(self, client):
        """POST /api/auth/refresh avec un refresh_token valide retourne de nouveaux tokens."""
        email = "refresh_flow@example.com"
        reg = _register(client, email)
        refresh_token = reg.cookies.get("refresh_token")

        response = client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": refresh_token} if refresh_token else {},
        )
        assert response.status_code == 200, response.text

    async def test_logout_succeeds(self, client):
        """POST /api/auth/logout avec un token valide retourne 200."""
        email = "logout_user@example.com"
        reg = _register(client, email)
        token = reg.cookies.get("access_token")

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "Déconnecté" in body.get("detail", "")

    async def test_admin_register_by_non_admin_returns_403(self, client):
        """Un utilisateur non-admin ne peut pas accéder à POST /api/auth/admin/register."""
        email = "non_admin@example.com"
        reg = _register(client, email)
        token = reg.cookies.get("access_token")

        response = client.post(
            "/api/auth/admin/register",
            json={
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": "AdminPass123!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403, response.text

    async def test_me_returns_correct_user_info(self, client):
        """GET /api/auth/users/me retourne les bonnes informations de l'utilisateur."""
        email = "me_info@example.com"
        reg = _register(client, email, username="meuser")
        token = reg.cookies.get("access_token")

        response = client.get(
            "/api/auth/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["email"] == email
        assert body["username"] == "meuser"
