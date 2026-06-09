import pytest
import base64
import os
import httpx
import asyncio
import datetime

from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock
from pydantic import ValidationError
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import timedelta
from backend.controllers.auth_controller import RefreshRequest, UserCreate, UserLogin, create_new_user, create_admin_user, login_for_access_token, get_current_user_info, get_current_user_tasks, logout, refresh_access_token
from backend.services.auth_service import  create_access_token, create_refresh_token, validate_refresh_token, revoke_refresh_token, authenticate_user, authenticate_user
from backend.middlewares.auth_middleware import get_current_user, is_admin

load_dotenv()

@pytest.mark.unit
def test_structure_user_create():
    """Test de la structure de UserCreate"""
    user_data = UserCreate(
        username="testuser",
        email=f"testuser@example.com",
        password="testpassword"
    )
    assert user_data.username == "testuser"
    assert user_data.email == f"testuser@example.com"
    assert user_data.password == "testpassword"
    assert isinstance(user_data.username, str)
    assert isinstance(user_data.email, str)
    assert isinstance(user_data.password, str)
    
@pytest.mark.unit
def test_structure_refresh_request():
    """Test de la structure de RefreshRequest"""
    form_data = RefreshRequest(
        refresh_token="valid_refresh_token"
    )
    assert form_data.refresh_token == "valid_refresh_token"
    assert isinstance(form_data.refresh_token, str)

@pytest.mark.unit
def test_structure_user_login():
    """Test de la structure de UserLogin"""
    form_data = UserLogin(
        email=f"testuser@example.com",
        password="testpassword"
    )
    
    assert form_data.email == f"testuser@example.com"
    assert form_data.password == "testpassword"
    assert isinstance(form_data.email, str)
    assert isinstance(form_data.password, str)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_new_user(mocker):
    """Test de la création d'un nouvel utilisateur"""
    mocker.patch('backend.controllers.auth_controller.create_access_token', return_value="fake_access_token")
    mocker.patch('backend.controllers.auth_controller.create_refresh_token', return_value="fake_refresh_token")
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None # Simule l'absence d'utilisateur existant
    mock_db.execute.return_value = mock_result # Simule l'exécution de la requête pour vérifier l'existence de l'utilisateur
    mock_db.commit.return_value = None # Simule la validation de la transaction
    mock_db.refresh.return_value = None # Simule le rafraîchissement de l'objet utilisateur après la créations
    
    user_data = UserCreate(
        username="testuser",
        email=f"testuser@example.com",
        password="testpassword"
    )
   
    result = await create_new_user(mock_db, user_data) 
   
    assert result["username"] == user_data.username
    assert result["email"] == user_data.email
    assert result["access_token"] == "fake_access_token"
    assert result["refresh_token"] == "fake_refresh_token"
    assert result["token_type"] == "bearer"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_admin_user(mocker):
    """Test de la création d'un nouvel utilisateur admin"""
    mocker.patch('backend.controllers.auth_controller.create_access_token', return_value="fake_access_token")
    mocker.patch('backend.controllers.auth_controller.create_refresh_token', return_value="fake_refresh_token")
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None # Simule l'absence d'utilisateur existant
    mock_db.execute.return_value = mock_result # Simule l'exécution de la requête pour vérifier l'existence de l'utilisateur
    mock_db.commit.return_value = None # Simule la validation de la transaction
    mock_db.refresh.return_value = None # Simule le rafraîchissement de l'objet utilisateur après la créations
    
    current_user = MagicMock()
    current_user.role = "admin"
    
    user_data = UserCreate(
        username="testuser",
        email=f"testuser@example.com",
        password="testpassword"
    )
   
    result = await create_admin_user(mock_db, current_user, user_data) 
   
    assert result["username"] == user_data.username
    assert result["email"] == user_data.email
    assert result["access_token"] == "fake_access_token"
    assert result["refresh_token"] == "fake_refresh_token"
    assert result["token_type"] == "bearer"
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_admin_user_non_admin(mocker):
    """Test de la création d'un nouvel utilisateur admin par un utilisateur non admin"""
    mock_db = AsyncMock()
    
    current_user = MagicMock()
    current_user.role = "user" # Simule un utilisateur non admin
    
    user_data = UserCreate(
        username="testuser",
        email=f"testuser@example.com",
        password="testpassword"
    )
    with pytest.raises(Exception) as exc_info:
        await create_admin_user(mock_db, current_user, user_data)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not enough permissions"    

@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_for_access_token(mocker):
    """Test de la connexion d'un utilisateur et de la génération des tokens"""
    mocker.patch('backend.controllers.auth_controller.create_access_token', return_value="fake_access_token")
    mocker.patch('backend.controllers.auth_controller.create_refresh_token', return_value="fake_refresh_token")
    
    mock_user = MagicMock()
    mock_user.email = f"testuser@example.com"
    mocker.patch('backend.controllers.auth_controller.authenticate_user', return_value=mock_user)
    
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_user # Simule la récupération de l'utilisateur depuis la base de données
    form_data = UserLogin(
        email=f"testuser@example.com",
        password="testpassword"
    )
    
    result = await login_for_access_token(form_data, mock_db)
    assert result["access_token"] == "fake_access_token"
    assert result["refresh_token"] == "fake_refresh_token"
    assert result["token_type"] == "bearer"
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_for_access_token_invalid_credentials(mocker):
    """Test de la connexion d'un utilisateur avec des identifiants invalides"""
    mocker.patch('backend.controllers.auth_controller.authenticate_user', return_value=None) # Simule l'échec de l'authentification
    
    mock_db = AsyncMock()
    form_data = UserLogin(
        email=f"testuser@example.com",
        password="wrongpassword"
    )
    
    with pytest.raises(Exception) as exc_info:
        await login_for_access_token(form_data, mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect email or password"
    
@pytest.mark.unit
def test_create_access_token():
    """Test de la création d'un token d'accès avec des données valides"""
    data = {"sub": "testuser@example.com"}
    token = create_access_token(data)
    assert isinstance(token, str)
    decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
    assert decoded["sub"] == "testuser@example.com"
    assert "exp" in decoded

@pytest.mark.unit
def test_create_refresh_token(mocker):
    """Test de la création d'un token de rafraîchissement avec un email valide"""
    mock_r = mocker.patch('backend.services.auth_service.r')
    email = "testuser@example.com"
    token = create_refresh_token(email)
    assert isinstance(token, str)
    assert len(token) > 0
    mock_r.set.assert_called_once_with(
        f"refresh:{token}",
        email,
        ex=7 * 86400
    )
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_access_token(mocker):
    """Test du rafraîchissement d'un token d'accès avec un token de rafraîchissement valide"""
    mocker.patch('backend.controllers.auth_controller.create_access_token', return_value="new_fake_access_token")
    mocker.patch('backend.controllers.auth_controller.create_refresh_token', return_value="new_fake_refresh_token")
    mocker.patch('backend.controllers.auth_controller.revoke_refresh_token')
    mocker.patch('backend.controllers.auth_controller.validate_refresh_token', return_value=f"testuser@example.com")
   
    body = RefreshRequest(refresh_token="valid_refresh_token")
    result = await refresh_access_token(body)
    
    assert result["access_token"] == "new_fake_access_token"
    assert result["refresh_token"] == "new_fake_refresh_token"
    assert result["token_type"] == "bearer"
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token(mocker):
    """Test du rafraîchissement d'un token d'accès avec un token de rafraîchissement invalide"""
    mocker.patch('backend.controllers.auth_controller.validate_refresh_token', return_value=None) # Simule un token de rafraîchissement invalide
    
    body = RefreshRequest(refresh_token="invalid_refresh_token")
    
    with pytest.raises(Exception) as exc_info:
        await refresh_access_token(body)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Refresh token invalide ou expiré"
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_logout(mocker):
    """Test de la déconnexion d'un utilisateur avec un token de rafraîchissement valide"""
    mocker.patch('backend.controllers.auth_controller.revoke_refresh_token')
    
    body = RefreshRequest(refresh_token="valid_refresh_token")
    result = await logout(body)
    
    assert result["detail"] == "Déconnecté avec succès"
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_current_user_info(mocker):
    """Test de la récupération des informations de l'utilisateur courant"""
    mock_user = MagicMock()
    mocker.patch('backend.controllers.auth_controller.get_current_user', return_value=mock_user)
    mock_user.username = "testuser"
    mock_user.email = f"testuser@example.com"
    mock_user.created_at = datetime.datetime(2024, 1, 1)
    mock_user.updated_at = datetime.datetime(2024, 1, 2)
    result = await get_current_user_info(mock_user)
    assert result["username"] == "testuser"
    assert result["email"] == "testuser@example.com"
    assert result["created_at"] == datetime.datetime(2024, 1, 1)
    assert result["updated_at"] == datetime.datetime(2024, 1, 2)
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_tasks(mocker):
    """Test de la récupération des tâches de l'utilisateur courant"""
    mock_user = MagicMock()
    mocker.patch('backend.controllers.auth_controller.get_current_user', return_value=mock_user)
    mock_user.username = "testuser"
    mock_user.email = f"testuser@example.com"
    mock_user.created_at = datetime.datetime(2024, 1, 1)
    mock_user.updated_at = datetime.datetime(2024, 1, 2)
    
    mock_epub = MagicMock()
    mock_epub.file_name = "fake_file_name"
    mock_epub.upload_date = "fake_upload_date"
    mock_epub.status = "fake_status"
    
    mock_task = MagicMock()
    mock_task.task_id_redis = "fake_task_id_redis"
    mock_task.epubs = [mock_epub]
    mock_task.status = "completed"
    mock_task.total_images = 3
    mock_task.processed_images = 3
    mock_task.created_at = datetime.datetime(2024, 1, 1)
    mock_task.started_at = datetime.datetime(2024, 1, 2)
    mock_task.completed_at = datetime.datetime(2024, 1, 3)
    
    mock_user.task = [mock_task]
    
    result = await get_current_user_tasks(mock_user)
    
    assert "tasks" in result
    assert isinstance(result["tasks"], list)
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["task_id_redis"] == "fake_task_id_redis"
    assert result["tasks"][0]["epubs"][0]["file_name"] == "fake_file_name"
    assert result["tasks"][0]["epubs"][0]["upload_date"] == "fake_upload_date"
    assert result["tasks"][0]["epubs"][0]["status"] == "fake_status"
    assert result["tasks"][0]["status"] == "completed"
    assert result["tasks"][0]["total_images"] == 3
    assert result["tasks"][0]["processed_images"] == 3
    assert result["tasks"][0]["created_at"] == datetime.datetime(2024, 1, 1)
    assert result["tasks"][0]["started_at"] == datetime.datetime(2024, 1, 2)
    assert result["tasks"][0]["completed_at"] == datetime.datetime(2024, 1, 3)
    
@pytest.mark.unit
def test_validate_refresh_token(mocker):
    """Test de la validation d'un token de rafraîchissement valide"""
    mock_r = mocker.patch('backend.services.auth_service.r')
    mock_r.get.return_value = b"testuser@example.com"

    result = validate_refresh_token("valid_refresh_token")

    assert result == "testuser@example.com"
    mock_r.get.assert_called_once_with("refresh:valid_refresh_token")

@pytest.mark.unit
def test_revoke_refresh_token(mocker):
    """Test de la révocation d'un token de rafraîchissement"""
    mock_r = mocker.patch('backend.services.auth_service.r')

    revoke_refresh_token("valid_refresh_token")

    mock_r.delete.assert_called_once_with("refresh:valid_refresh_token")
    
@pytest.mark.unit
def test_hash_and_verify_password(mocker):
    """Test du hachage et de la vérification d'un mot de passe"""
    from backend.services.auth_service import hash_password, verify_password
    
    password = "testpassword"
    hashed_password = hash_password(password)
    
    assert isinstance(hashed_password, str)
    assert hashed_password != password
    
    is_valid = verify_password(password, hashed_password)
    assert is_valid == True
    
    is_invalid = verify_password("wrongpassword", hashed_password)
    assert is_invalid == False
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user(mocker):
    """Test de la récupération d'un utilisateur depuis la base de données"""
    from backend.services.auth_service import get_user
    mock_user = MagicMock()
    mock_user.email = f"testuser@example.com"
    mock_user.username = "testuser"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
        
    result = await get_user(mock_db, mock_user.email)
    
    assert result.email == mock_user.email
    assert result.username == mock_user.username
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user(mocker):
    """Test de l'authentification d'un utilisateur avec des identifiants valides"""
    mock_user = MagicMock()
    mock_user.email = "testuser@example.com"
    mock_user.password_hash = "fake_hashed_password"

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    mocker.patch('backend.services.auth_service.verify_password', return_value=True)

    result = await authenticate_user(mock_db, mock_user.email, "testpassword")

    assert result.email == "testuser@example.com"
    assert result.password_hash == "fake_hashed_password"

# ─── Bloc 1 : Modèles Pydantic — champs manquants ───────────────────────────

@pytest.mark.unit
def test_user_create_missing_username():
    """Test que UserCreate lève une ValidationError si username est absent"""
    with pytest.raises(ValidationError):
        UserCreate(email="testuser@example.com", password="testpassword")

@pytest.mark.unit
def test_user_create_missing_email():
    """Test que UserCreate lève une ValidationError si email est absent"""
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", password="testpassword")

@pytest.mark.unit
def test_user_create_missing_password():
    """Test que UserCreate lève une ValidationError si password est absent"""
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="testuser@example.com")

@pytest.mark.unit
def test_user_login_missing_email():
    """Test que UserLogin lève une ValidationError si email est absent"""
    with pytest.raises(ValidationError):
        UserLogin(password="testpassword")

@pytest.mark.unit
def test_user_login_missing_password():
    """Test que UserLogin lève une ValidationError si password est absent"""
    with pytest.raises(ValidationError):
        UserLogin(email="testuser@example.com")

@pytest.mark.unit
def test_refresh_request_missing_token():
    """Test que RefreshRequest lève une ValidationError si refresh_token est absent"""
    with pytest.raises(ValidationError):
        RefreshRequest()

# ─── Bloc 2 : Controller — cas d'erreur ─────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_new_user_existing_email():
    """Test que create_new_user lève une 409 si l'email existe déjà"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = MagicMock()  # email déjà pris
    mock_db.execute.return_value = mock_result

    user_data = UserCreate(username="testuser", email="testuser@example.com", password="testpassword")

    with pytest.raises(Exception) as exc_info:
        await create_new_user(mock_db, user_data)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Cet email est déjà utilisé."

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_admin_user_existing_email():
    """Test que create_admin_user lève une 409 si l'email existe déjà"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = MagicMock()  # email déjà pris
    mock_db.execute.return_value = mock_result

    current_user = MagicMock()
    current_user.role = "admin"
    user_data = UserCreate(username="testuser", email="testuser@example.com", password="testpassword")

    with pytest.raises(Exception) as exc_info:
        await create_admin_user(mock_db, current_user, user_data)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Cet email est déjà utilisé."

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_tasks_empty():
    """Test que get_current_user_tasks retourne une liste vide si l'utilisateur n'a pas de tâches"""
    mock_user = MagicMock()
    mock_user.task = []

    result = await get_current_user_tasks(mock_user)

    assert result == {"tasks": []}
    assert len(result["tasks"]) == 0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_tasks_no_epubs():
    """Test que get_current_user_tasks gère une tâche sans epub"""
    mock_task = MagicMock()
    mock_task.task_id_redis = "fake_task_id_redis"
    mock_task.epubs = []
    mock_task.status = "completed"
    mock_task.total_images = 0
    mock_task.processed_images = 0
    mock_task.created_at = datetime.datetime(2024, 1, 1)
    mock_task.started_at = datetime.datetime(2024, 1, 2)
    mock_task.completed_at = datetime.datetime(2024, 1, 3)

    mock_user = MagicMock()
    mock_user.task = [mock_task]

    result = await get_current_user_tasks(mock_user)

    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["epubs"] == []

# ─── Bloc 3 : Service — cas d'erreur et branches ────────────────────────────

@pytest.mark.unit
def test_validate_refresh_token_not_found(mocker):
    """Test que validate_refresh_token retourne None si le token n'existe pas dans Redis"""
    mock_r = mocker.patch('backend.services.auth_service.r')
    mock_r.get.return_value = None

    result = validate_refresh_token("unknown_token")

    assert result is None

@pytest.mark.unit
def test_validate_refresh_token_as_string(mocker):
    """Test que validate_refresh_token retourne l'email tel quel si Redis retourne une str"""
    mock_r = mocker.patch('backend.services.auth_service.r')
    mock_r.get.return_value = "testuser@example.com"  # str, pas bytes

    result = validate_refresh_token("valid_refresh_token")

    assert result == "testuser@example.com"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_not_found(mocker):
    """Test que get_user retourne None si l'utilisateur n'existe pas"""
    from backend.services.auth_service import get_user

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await get_user(mock_db, "unknown@example.com")

    assert result is None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Test que authenticate_user retourne None si l'utilisateur n'existe pas"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await authenticate_user(mock_db, "unknown@example.com", "testpassword")

    assert result is None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(mocker):
    """Test que authenticate_user retourne None si le mot de passe est incorrect"""
    mock_user = MagicMock()
    mock_user.email = "testuser@example.com"
    mock_user.password_hash = "fake_hashed_password"

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    mocker.patch('backend.services.auth_service.verify_password', return_value=False)

    result = await authenticate_user(mock_db, mock_user.email, "wrongpassword")

    assert result is None

@pytest.mark.unit
def test_create_access_token_with_expires_delta():
    """Test de la création d'un token d'accès avec un expires_delta explicite"""
    data = {"sub": "testuser@example.com"}
    delta = timedelta(minutes=30)

    token = create_access_token(data, expires_delta=delta)

    assert isinstance(token, str)
    assert len(token) > 0

# ─── Bloc 4 : Middleware get_current_user ────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_valid_token(mocker):
    """Test que get_current_user retourne l'utilisateur avec un token valide"""
    mock_user = MagicMock()
    mock_user.email = "testuser@example.com"

    mocker.patch('backend.middlewares.auth_middleware.jwt.decode', return_value={"sub": "testuser@example.com"})

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await get_current_user("fake_valid_token", mock_db)

    assert result == mock_user

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_expired_token(mocker):
    """Test que get_current_user lève une 401 si le token est expiré"""
    mocker.patch('backend.middlewares.auth_middleware.jwt.decode', side_effect=ExpiredSignatureError)

    mock_db = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await get_current_user("expired_token", mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mocker):
    """Test que get_current_user lève une 401 si le token est invalide"""
    mocker.patch('backend.middlewares.auth_middleware.jwt.decode', side_effect=InvalidTokenError)

    mock_db = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await get_current_user("invalid_token", mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_no_sub_in_payload(mocker):
    """Test que get_current_user lève une 401 si le payload ne contient pas de sub"""
    mocker.patch('backend.middlewares.auth_middleware.jwt.decode', return_value={"sub": None})

    mock_db = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await get_current_user("token_without_sub", mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mocker):
    """Test que get_current_user lève une 401 si l'utilisateur n'existe pas en BDD"""
    mocker.patch('backend.middlewares.auth_middleware.jwt.decode', return_value={"sub": "unknown@example.com"})

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    with pytest.raises(Exception) as exc_info:
        await get_current_user("valid_token_unknown_user", mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

# ─── Bloc 5 : Middleware is_admin ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_admin_valid():
    """Test que is_admin ne lève pas d'exception si l'utilisateur est admin"""
    mock_user = MagicMock()
    mock_user.role = "admin"

    await is_admin(mock_user)  # ne doit pas lever d'exception