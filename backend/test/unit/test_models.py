import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from typing import List
from fastapi.testclient import TestClient

# ── Mock heavy ML dependencies BEFORE importing model modules ──
sys.modules.setdefault("transformers", MagicMock())
sys.modules.setdefault("torch", MagicMock())

# ── Mock the local 'utils' module used by the model microservices ──
# (each model does: from utils import ImageRequest, ModelConfig, process_image)
class FakeImageRequest(BaseModel):
    images: List[str] = []


utils_mock = MagicMock()
utils_mock.ImageRequest = FakeImageRequest
sys.modules["utils"] = utils_mock

from backend.models.model1.saleforce_cpu_large import app as salesforce_app
from backend.models.model2.florence2_large import app as florence_app
from backend.models.model3.git_large import app as git_app

_MOCK_RESULT = {
    "success": True,
    "english_description": "a dog on a beach",
    "french_description": "un chien sur une plage",
    "generation_time": 0.5,
}
_MOCK_PROCESSOR = MagicMock()
_MOCK_MODEL = MagicMock()


# ─────────────────────────────────────────────
# Les 3 microservices modèles (model1/2/3) exposent le même contrat
# (GET / + POST /describe). On les teste via un seul jeu paramétré.
# ─────────────────────────────────────────────

MODELS = [
    pytest.param(
        salesforce_app,
        "backend.models.model1.saleforce_cpu_large",
        "salesforce_cpu_large",
        id="salesforce",
    ),
    pytest.param(
        florence_app,
        "backend.models.model2.florence2_large",
        "florence2_large",
        id="florence",
    ),
    pytest.param(
        git_app,
        "backend.models.model3.git_large",
        "git_large",
        id="git",
    ),
]


def _patch_model(mocker, module):
    """Mocke le chargement du modèle et process_image pour un microservice donné."""
    mocker.patch(f"{module}._get_model", return_value=(_MOCK_PROCESSOR, _MOCK_MODEL))
    mocker.patch(f"{module}.process_image", new=AsyncMock(return_value=_MOCK_RESULT))


@pytest.mark.parametrize("app, module, status_label", MODELS)
class TestModelDescribeEndpoint:
    @pytest.mark.unit
    def test_root_returns_status(self, app, module, status_label):
        resp = TestClient(app).get("/")
        assert resp.status_code == 200
        assert status_label in resp.json()["status"]

    @pytest.mark.unit
    def test_describe_empty_list_returns_empty(self, mocker, app, module, status_label):
        _patch_model(mocker, module)
        resp = TestClient(app).post("/describe", json={"images": []})
        assert resp.status_code == 200
        assert resp.json() == {"results": []}

    @pytest.mark.unit
    def test_describe_single_image_returns_result(self, mocker, app, module, status_label):
        _patch_model(mocker, module)
        resp = TestClient(app).post("/describe", json={"images": ["aGVsbG8="]})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["success"] is True
        assert body["results"][0]["english_description"] == "a dog on a beach"
        assert body["results"][0]["french_description"] == "un chien sur une plage"

    @pytest.mark.unit
    def test_describe_multiple_images(self, mocker, app, module, status_label):
        _patch_model(mocker, module)
        resp = TestClient(app).post("/describe", json={"images": ["img1", "img2", "img3"]})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 3


# ─────────────────────────────────────────────
# backend/utils.py — process_image (logique commune aux 3 modèles)
# ─────────────────────────────────────────────


class TestProcessImage:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_url_image_success(self, mocker):
        from backend.utils import process_image, ModelConfig

        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mocker.patch("backend.utils.requests.get", return_value=MagicMock())
        mocker.patch("backend.utils.Image.open", return_value=mock_image)

        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_processor.return_value = {"input_ids": MagicMock()}
        mock_model.generate.return_value = [MagicMock()]
        mock_processor.decode.return_value = "a cat sitting"

        mocker.patch(
            "backend.utils.GoogleTranslator",
            return_value=MagicMock(translate=MagicMock(return_value="un chat assis")),
        )

        config = ModelConfig()
        result = await process_image(
            "https://example.com/image.jpg", mock_processor, mock_model, config
        )

        assert result["success"] is True
        assert result["english_description"] == "a cat sitting"
        assert result["french_description"] == "un chat assis"
        assert result["generation_time"] >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_base64_image_success(self, mocker):
        from backend.utils import process_image, ModelConfig

        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mocker.patch("backend.utils.base64.b64decode", return_value=b"fake_bytes")
        mocker.patch("backend.utils.Image.open", return_value=mock_image)

        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_processor.return_value = {"input_ids": MagicMock()}
        mock_model.generate.return_value = [MagicMock()]
        mock_processor.decode.return_value = "a mountain"

        mocker.patch(
            "backend.utils.GoogleTranslator",
            return_value=MagicMock(translate=MagicMock(return_value="une montagne")),
        )

        config = ModelConfig()
        result = await process_image("aGVsbG8=", mock_processor, mock_model, config)

        assert result["success"] is True
        assert result["english_description"] == "a mountain"
        assert result["french_description"] == "une montagne"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_type_error_returns_error_dict(self, mocker):
        from backend.utils import process_image, ModelConfig

        mocker.patch("backend.utils.base64.b64decode", return_value=b"fake")
        mocker.patch(
            "backend.utils.Image.open", side_effect=TypeError("format non supporté")
        )

        config = ModelConfig()
        result = await process_image("aGVsbG8=", MagicMock(), MagicMock(), config)

        assert "error" in result
        assert "format non supporté" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pixel_values_only_config(self, mocker):
        from backend.utils import process_image, ModelConfig

        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mocker.patch("backend.utils.base64.b64decode", return_value=b"fake")
        mocker.patch("backend.utils.Image.open", return_value=mock_image)

        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_processor.return_value.pixel_values = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_processor.batch_decode.return_value = ["two people walking"]

        mocker.patch(
            "backend.utils.GoogleTranslator",
            return_value=MagicMock(
                translate=MagicMock(return_value="deux personnes qui marchent")
            ),
        )

        config = ModelConfig(
            use_pixel_values_only=True,
            use_batch_decode=True,
            generate_kwargs={"max_length": 50},
        )
        result = await process_image("aGVsbG8=", mock_processor, mock_model, config)

        assert result["success"] is True
        assert result["english_description"] == "two people walking"
        assert result["french_description"] == "deux personnes qui marchent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_post_process_config(self, mocker):
        from backend.utils import process_image, ModelConfig

        mock_image = MagicMock()
        mock_image.width = 640
        mock_image.height = 480
        mock_image.convert.return_value = mock_image
        mocker.patch("backend.utils.requests.get", return_value=MagicMock())
        mocker.patch("backend.utils.Image.open", return_value=mock_image)

        task = "<MORE_DETAILED_CAPTION>"
        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.__getitem__ = MagicMock(side_effect=lambda k: MagicMock())
        mock_processor.return_value = mock_inputs
        mock_model.generate.return_value = MagicMock()
        mock_processor.batch_decode.return_value = ["a detailed forest scene"]
        mock_processor.post_process_generation.return_value = {
            task: "a detailed forest scene"
        }

        mocker.patch(
            "backend.utils.GoogleTranslator",
            return_value=MagicMock(
                translate=MagicMock(return_value="une scène de forêt détaillée")
            ),
        )

        config = ModelConfig(
            task=task,
            use_batch_decode=True,
            skip_special_tokens=False,
            post_process=True,
            generate_kwargs={"max_new_tokens": 1024},
        )
        result = await process_image(
            "https://example.com/forest.jpg", mock_processor, mock_model, config
        )

        assert result["success"] is True
        assert result["english_description"] == "a detailed forest scene"
        assert result["french_description"] == "une scène de forêt détaillée"
