import pytest
import base64
import os
import httpx
from dotenv import load_dotenv
load_dotenv()
from unittest.mock import AsyncMock
from backend.utils.image_describe import get_image_describe
from backend.utils.image_request import ImageRequest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_return_correct_structure(mocker):
    """Test de get_image_describe retourne la structure attendue."""
    mock_response = AsyncMock(
        status_code=200,
        json=lambda: {
            "results": [
                {
                    "success": True,
                    "english_description": "A cat",
                    "french_description": "Un chat",
                    "generation_time": 0.5
                },
                {
                    "success": True,
                    "english_description": "A dog",
                    "french_description": "Un chien",
                    "generation_time": 0.5
                }
                
            ]
        }
    )
    mocker.patch('httpx.AsyncClient.post', return_value=mock_response)
    
    img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
    img2_b64 = base64.b64encode(b"fake_image_data_2").decode("utf-8")
    img_list = [img1_b64, img2_b64]
    
    result = await get_image_describe(img_list)
    
    assert isinstance(result, dict)
    assert "images" in result
    assert "total_images" in result
    assert "time" in result
    assert result["images"]["image_0"].keys() == {"index", "salesforce_blip", "florence2", "git_large"}
    assert result["images"]["image_1"].keys() == {"index", "salesforce_blip", "florence2", "git_large"}
    assert isinstance(result["time"], float)
    assert result["time"] >= 0
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_return_not_correct_structure(mocker):
    """Test de get_image_describe ne retourne pas une structure incorrecte."""
    mocker_response = AsyncMock(
        status_code=200,
        json=lambda: {
            "wrong_key": "wrong_value"
        }
    )
    mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
    img_list = [img1_b64]
    result = await get_image_describe(img_list)    
    assert not isinstance(result, list)
    assert "wrong_key" not in result

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_error_handling(mocker):
    """Test de la gestion des erreurs dans get_image_describe."""
    
    mocker.patch('httpx.AsyncClient.post', side_effect=Exception("Service unavailable"))
    
    img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
    img_list = [img1_b64]
    
    result = await get_image_describe(img_list)
    
    assert isinstance(result, dict)
    assert "images" in result
    assert "total_images" in result
    assert "time" in result

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_empty_list(mocker):
    """Test de get_image_describe avec une liste d'images vide."""
    mocker_response = AsyncMock(
        status_code=200,
        json=lambda: {
            "results": []
        }
    )
    mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    img_list = []
    result = await get_image_describe(img_list)
    
    assert isinstance(result, dict)
    assert result["images"] == {}
    assert result["total_images"] == 0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_call_models(mocker):
    """Garantie que get_image_describe appelle les modèles externes."""
    mocker_response = mocker.Mock(
        status_code=200,
        json=lambda: {
            "results": [
                {
                    "success": True,
                    "english_description": "A cat",
                    "french_description": "Un chat",
                    "generation_time": 0.3
                }
            ]
        }
    )
    post_mock = mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    img_1_bs64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
    img_2_bs64 = base64.b64encode(b"fake_image_data_2").decode("utf-8")
    img_bs64_list = [img_1_bs64, img_2_bs64]
    
    result = await get_image_describe(img_bs64_list)
    assert "images" in result
    assert post_mock.call_count == 3

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_batching(mocker):
    """Test de la logique de batching dans get_image_describe."""
    mocker_response = mocker.Mock(
        status_code=200,
        json=lambda: {
            "results": [
                {"success": True, 
                    "english_description": f"desc {i}", 
                    "french_description": f"desc fr {i}",
                    "generation_time": 0.4
                }
                for i in range(5)  # Traitement par lots de 5
            ]
        }
    )
    post_mock = mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    img_bs64_list = [base64.b64encode(f"fake_image_data_{i}".encode()).decode("utf-8") for i in range(12)]
    result = await get_image_describe(img_bs64_list)
    
    assert post_mock.call_count == 9  
    assert "images" in result

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_calls_all_models(mocker):
    """Test que get_image_describe appelle tous les modèles pour chaque batch."""
    mocker_response = mocker.Mock(
        status_code=200,
        json=lambda: {
            "results": [
                {"success": True, 
                    "english_description": f"desc", 
                    "french_description": f"desc fr",
                    "generation_time": 0.4
                }
            ]
        }
    )
    
    img_bs64_list = [base64.b64encode(f"fake_image_data_{i}".encode()).decode("utf-8") for i in range(7)]
    
    post_mock = mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    result = await get_image_describe(img_bs64_list)
    
    assert post_mock.call_count == 6  
    assert "images" in result
    
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_image_describe_model_returns_error(mocker):
    """Test la gestion des erreurs retournées par les modèles dans get_image_describe."""
    mocker_response = mocker.Mock(
        status_code=500, 
        text="Internal Server Error"
    )
    
    mocker.patch('httpx.AsyncClient.post', return_value=mocker_response)
    
    img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
    img_list = [img1_b64]
    
    result = await get_image_describe(img_list)
    
    assert isinstance(result, dict)
    assert "images" in result
    assert "total_images" in result
    assert result["total_images"] == 0

@pytest.mark.unit
def test_request_image_request_valid():
    """Test de la validation de ImageRequest avec des images valides."""
    img_local = ["fake_image_data_1", "fake_image_data_2"]
    request = ImageRequest(images=img_local)
    assert request.images == img_local
    
@pytest.mark.unit
def test_request_image_request_invalid():
    """Test de la validation de ImageRequest avec des images invalides."""
    img_local = "not_a_list"
    with pytest.raises(Exception):
        ImageRequest(images=img_local)
        
@pytest.mark.unit
def test_request_image_request_none():
    """Test avec None au lieu d'une liste."""
    with pytest.raises(Exception):
        ImageRequest(images=None)
        
@pytest.mark.unit
def test_request_image_request_empty():
    """Test avec une chaîne au lieu d'une liste."""
    img_local = ["", ""]
    request = ImageRequest(images=img_local)
    assert request.images == img_local