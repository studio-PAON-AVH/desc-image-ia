import pytest
import sys
import httpx
import os
import warnings
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
import backend.api.api as api_module
from backend.redis.redis import redis_server_test

api_module.r = redis_server_test()

@pytest.fixture
def client():
    """Fixture pour le client de test FastAPI"""
    return TestClient(api_module.app)

@pytest.fixture
def image(tmp_path):
    """Fixture pour créer une image de test temporaire"""
    image_file = tmp_path / "C:\\Users\\adminpaon\\dev\\mission-apprentissage-IA\\proto-IA\\image\\palace.jpg"
    image_file.write_bytes(b"fake image data")
    return str(image_file)

@pytest.fixture
def image_invalid(tmp_path):
    """Fixture pour créer une image de test temporaire invalide"""
    image_file = tmp_path / "test_image.docx"
    return str(image_file)

@pytest.mark.integration
def test_check_redis():
    """Test de connexion à Redis"""
    try:
        api_module.r.ping()
    except : 
        pytest.fail("Connexion à Redis a échoué.")
        
def check_model_serving(url):
    """Vérifier si un service de modèle est disponible"""
    try:
        response = httpx.get(url, timeout=5)
        if response.status_code == 200:
            return True
        base_url = url.rsplit('/', 1)[0]
        response = httpx.get(base_url, timeout=5)
        return response.status_code in [200, 404, 405]
    
    except Exception as e:
        return False

@pytest.mark.integration
def test_model_service_available():
    """Vérifier la disponibilité des services de modèles avant d'exécuter les tests"""
    services = {
        "salesforce_blip": os.getenv('URL_SALESFORCE_CPU_LARGE'),
        "florence_2_large": os.getenv('URL_FLORANCE_2_LARGE'),
        "git_large": os.getenv('URL_GIT_LARGE')
    }
    unavailable = [name for name, url in services.items() if not check_model_serving(url)]
    if unavailable:
        pytest.fail(f"Services indisponibles: {', '.join(unavailable)}")
        
@pytest.mark.integration
def test_api_started(client):
    """Test de démarrage de l'API via le endpoint racine"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"API": "Success"}

@pytest.mark.integration
def test_post_create_task_predict(client, image):
    """Test de création de tâche via le endpoint /predict"""
    response = client.post(
        "/predict",
        json={"images": [image]}
    )
    assert response.status_code == 201
    assert "task_id" in response.json()
    task_id = response.json()["task_id"]
    result = api_module.r.get(task_id)
    assert result is not None

@pytest.mark.integration
def test_get_task_result_pending(client, image):
    """Test de récupération d'une tâche en attente via le endpoint /predict/{task_id}"""
    response = client.post("/predict", json={"images": [image]})
    assert response.status_code == 201
    task_id = response.json()["task_id"]
    
    response = client.get(f"/predict/{task_id}")
    assert response.status_code == 200
    
    """Vérifie la structure de la réponse"""
    result = response.json()["result"]

    assert "images" in result
    assert "total_images" in result
    assert "time" in result
    
    assert result["total_images"] > 0
    
    assert "image_0" in result["images"]
    image_result = result["images"]["image_0"]
    
    assert "index" in image_result
    assert image_result["index"] == 0    
    assert "salesforce_blip" in image_result
    assert "florence2" in image_result
    assert "git_large" in image_result

@pytest.mark.integration
def test_get_task_result_invalid_id(client):
    """Test de récupération d'une tâche avec un ID invalide via le endpoint /predict/{task_id}"""
    invalid_task_id = "invalid_task_id_123"
    response = client.get(f"/predict/{invalid_task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche non trouvée"
    
@pytest.mark.integration
def test_post_create_task_with_image_invalid(client, image_invalid):
    """Test de création de tâche avec une image corrompue via le endpoint /predict"""
    response = client.post(
        "/predict",
        json={"images": [image_invalid]}
    )
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Erreur de traitement" in response.json()["detail"]
    
@pytest.mark.integration
def test_multiple_tasks_parallel(client, image, tmp_path):
    """Test de création de plusieurs tâches en parallèle via le endpoint /predict"""
    image2 = tmp_path / "test_image2.jpg"
    image2.write_bytes(b"other fake image data")
    response1 = client.post("/predict", json={"images": [image]})
    response2 = client.post("/predict", json={"images": [str(image2)]})
    assert response1.status_code == 201
    assert response2.status_code == 201
    task_id1 = response1.json()["task_id"]
    task_id2 = response2.json()["task_id"]
    assert task_id1 != task_id2
    assert api_module.r.get(task_id1) is not None
    assert api_module.r.get(task_id2) is not None
    
@pytest.mark.integration
def test_task_status_pending(client, image):
    """Test de récupération d'une tâche en statut 'en attente' via le endpoint /predict/{task_id}"""
    response = client.post("/predict", json={"images": [image]})
    task_id = response.json()["task_id"]
    api_module.r.set(task_id, '{"status": "en attente"}')
    response = client.get(f"/predict/{task_id}")
    assert response.status_code == 202
    assert response.json()["message"] == "Tâche en attente ou en cours" 
    
@pytest.mark.integration
def test_predict_malformed_json(client):
    """Test avec body JSON malformé"""
    malformed_json = "{'images': [invalid_json]}"
    response = client.post(
        "/predict",
        content=malformed_json,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert len(detail) > 0

def test_predict_incorrect_type(client):
    """Test avec un type de données incorrect"""
    response = client.post(
        "/predict",
        json={"images": True}
    )
    assert response.status_code == 422
    assert "detail" in response.json()
    detail = response.json()["detail"]
    assert isinstance(detail, list)

@pytest.mark.integration
def test_predict_incorrect_images_type(client):
    """Test avec types de données incorrects pour le champ 'images'"""
    # Cas 1: 'images' est une string au lieu d'une liste
    response = client.post(
        "/predict",
        json={"images": "not-a-list"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    
    # Cas 2: 'images' est une liste mais contient des éléments non-string
    response = client.post(
        "/predict",
        json={"images": [123, 456]}
    )
    assert response.status_code == 422
    assert "detail" in response.json()
    detail = response.json()["detail"]
    assert isinstance(detail, list) 
    
@pytest.mark.integration
def test_missing_field_request_body(client):
    """Test avec un champ manquant dans le body de la requête"""
    response = client.post(
        "/predict",
        json={}
    )
    assert response.status_code == 422
    assert "detail" in response.json()
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    
@pytest.mark.integration
def test_batch_many_images(client, tmp_path):
    """Test avec un grand nombre d'images dans une seule requête"""
    image_files = []
    for i in range(50):
        img_path = tmp_path / f"test_image_{i}.jpg"
        img_path.write_bytes(b"fake image data " + bytes(str(i), 'utf-8'))
        image_files.append(str(img_path))
    
    response = client.post(
        "/predict",
        json={"images": image_files}
    )
    assert response.status_code == 201
    assert "task_id" in response.json()
    task_id = response.json()["task_id"]
    result = api_module.r.get(task_id)
    assert result is not None

@pytest.mark.integration
def test_task_processing_task(client, image):
    """Test de récupération d'une tâche qui a rencontré une erreur lors du traitement"""
    # Création de la tâche
    response = client.post("/predict", json={"images": [image]})
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    # Simuler une erreur en stockant directement un message d'erreur dans Redis
    api_module.r.set(task_id, '{"error": "Service de modèle indisponible"}')

    # Vérifier que l'API retourne bien une erreur 500 et le message d'erreur
    response = client.get(f"/predict/{task_id}")
    assert response.status_code == 500
    assert "erreur" in response.json()["detail"].lower()