import sys
import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from typing import List

load_dotenv()

# ── Fake Pydantic model so FastAPI route decorators don't crash ──
class FakeImageRequest(BaseModel):
    images: List[str] = []

fake_utils_image_request = MagicMock()
fake_utils_image_request.ImageRequest = FakeImageRequest

# ── Mock heavy dependencies BEFORE importing model modules ──
sys.modules.setdefault('transformers', MagicMock())
sys.modules.setdefault('torch', MagicMock())
sys.modules.setdefault('utils', MagicMock())
sys.modules.setdefault('utils.image_request', fake_utils_image_request)

from backend.models.model1.saleforce_cpu_large import (
    process_image as salesforce_process_image,
    describe_with_salesforce_cpu_large,
)
from backend.models.model2.florence2_large import (
    process_image as florence_process_image,
    describe_image_with_florance2_large,
)
from backend.models.model3.git_large import (
    process_image as git_process_image,
    describe_image_with_git_large,
)


# ─────────────────────────────────────────────
# Model 1 — Salesforce BLIP (CPU Large)
# ─────────────────────────────────────────────

class TestSalesforceModel:

    class TestProcessImage:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_url_success(self, mocker):
            """Test process_image avec une URL valide retourne les descriptions."""
            mock_raw_image = MagicMock()
            mocker.patch("backend.models.model1.saleforce_cpu_large.requests.get", return_value=MagicMock())
            mocker.patch("backend.models.model1.saleforce_cpu_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            mock_processor.return_value = {"input_ids": MagicMock()}
            mock_model.generate.return_value = [MagicMock()]
            mock_processor.decode.return_value = "a dog on a beach"

            mocker.patch(
                "backend.models.model1.saleforce_cpu_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="un chien sur une plage"))
            )

            result = await salesforce_process_image("https://example.com/image.jpg", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "a dog on a beach"
            assert result["french_description"] == "un chien sur une plage"
            assert result["generation_time"] >= 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_base64_success(self, mocker):
            """Test process_image avec une image base64 valide."""
            mock_raw_image = MagicMock()
            mocker.patch("backend.models.model1.saleforce_cpu_large.base64.b64decode", return_value=b"fake_bytes")
            mocker.patch("backend.models.model1.saleforce_cpu_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            mock_processor.return_value = {"input_ids": MagicMock()}
            mock_model.generate.return_value = [MagicMock()]
            mock_processor.decode.return_value = "a cat sitting"

            mocker.patch(
                "backend.models.model1.saleforce_cpu_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="un chat assis"))
            )

            result = await salesforce_process_image("aGVsbG8=", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "a cat sitting"
            assert result["french_description"] == "un chat assis"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_error(self, mocker):
            """Test process_image retourne un dict avec 'error' en cas d'exception."""
            mocker.patch(
                "backend.models.model1.saleforce_cpu_large.requests.get",
                side_effect=Exception("Connexion refusée")
            )

            mock_processor = MagicMock()
            mock_model = MagicMock()

            result = await salesforce_process_image("https://example.com/bad.jpg", mock_processor, mock_model)

            assert "error" in result
            assert "Connexion refusée" in result["error"]

    class TestDescribeWithSalesforceCpuLarge:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_returns_results_list(self, mocker):
            """Test que describe_with_salesforce_cpu_large retourne une liste de résultats."""
            mock_result = {
                "success": True,
                "english_description": "a dog",
                "french_description": "un chien",
                "generation_time": 0.5
            }
            mocker.patch(
                "backend.models.model1.saleforce_cpu_large.process_image",
                new=AsyncMock(return_value=mock_result)
            )

            result = await describe_with_salesforce_cpu_large(["img1", "img2"])

            assert "results" in result
            assert len(result["results"]) == 2

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_empty_list(self, mocker):
            """Test que describe_with_salesforce_cpu_large retourne une liste vide."""
            result = await describe_with_salesforce_cpu_large([])

            assert result == {"results": []}


# ─────────────────────────────────────────────
# Model 2 — Florence-2
# ─────────────────────────────────────────────

class TestFlorence2Model:

    class TestProcessImage:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_url_success(self, mocker):
            """Test process_image avec une URL valide retourne les descriptions."""
            mock_raw_image = MagicMock()
            mock_raw_image.width = 640
            mock_raw_image.height = 480
            mocker.patch("backend.models.model2.florence2_large.requests.get", return_value=MagicMock())
            mocker.patch("backend.models.model2.florence2_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            task = "<MORE_DETAILED_CAPTION>"
            mock_inputs = MagicMock()
            mock_inputs.__getitem__ = MagicMock(side_effect=lambda k: MagicMock())
            mock_processor.return_value = mock_inputs
            mock_processor.batch_decode.return_value = ["a detailed description of a forest"]
            mock_processor.post_process_generation.return_value = {task: "a detailed description of a forest"}

            mocker.patch(
                "backend.models.model2.florence2_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="une description détaillée d'une forêt"))
            )

            result = await florence_process_image("https://example.com/forest.jpg", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "a detailed description of a forest"
            assert result["french_description"] == "une description détaillée d'une forêt"
            assert result["generation_time"] >= 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_base64_success(self, mocker):
            """Test process_image avec une image base64 valide."""
            mock_raw_image = MagicMock()
            mock_raw_image.width = 320
            mock_raw_image.height = 240
            mocker.patch("backend.models.model2.florence2_large.base64.b64decode", return_value=b"fake_bytes")
            mocker.patch("backend.models.model2.florence2_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            task = "<MORE_DETAILED_CAPTION>"
            mock_inputs = MagicMock()
            mock_inputs.__getitem__ = MagicMock(side_effect=lambda k: MagicMock())
            mock_processor.return_value = mock_inputs
            mock_processor.batch_decode.return_value = ["a red car"]
            mock_processor.post_process_generation.return_value = {task: "a red car"}

            mocker.patch(
                "backend.models.model2.florence2_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="une voiture rouge"))
            )

            result = await florence_process_image("aGVsbG8=", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "a red car"
            assert result["french_description"] == "une voiture rouge"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_error(self, mocker):
            """Test process_image retourne un dict avec 'error' en cas d'exception."""
            mocker.patch(
                "backend.models.model2.florence2_large.requests.get",
                side_effect=Exception("Timeout")
            )

            mock_processor = MagicMock()
            mock_model = MagicMock()

            result = await florence_process_image("https://example.com/bad.jpg", mock_processor, mock_model)

            assert "error" in result
            assert "Timeout" in result["error"]

    class TestDescribeImageWithFlorance2Large:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_returns_results_list(self, mocker):
            """Test que describe_image_with_florance2_large retourne une liste de résultats."""
            mock_result = {
                "success": True,
                "english_description": "a forest",
                "french_description": "une forêt",
                "generation_time": 1.2
            }
            mocker.patch(
                "backend.models.model2.florence2_large.process_image",
                new=AsyncMock(return_value=mock_result)
            )

            result = await describe_image_with_florance2_large(["img1", "img2"])

            assert "results" in result
            assert len(result["results"]) == 2

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_empty_list(self, mocker):
            """Test que describe_image_with_florance2_large retourne une liste vide."""
            result = await describe_image_with_florance2_large([])

            assert result == {"results": []}


# ─────────────────────────────────────────────
# Model 3 — Microsoft GIT Large
# ─────────────────────────────────────────────

class TestGitLargeModel:

    class TestProcessImage:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_url_success(self, mocker):
            """Test process_image avec une URL valide retourne les descriptions."""
            mock_raw_image = MagicMock()
            mocker.patch("backend.models.model3.git_large.requests.get", return_value=MagicMock())
            mocker.patch("backend.models.model3.git_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            mock_processor.return_value.pixel_values = MagicMock()
            mock_model.generate.return_value = MagicMock()
            mock_processor.batch_decode.return_value = ["two people walking"]

            mocker.patch(
                "backend.models.model3.git_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="deux personnes qui marchent"))
            )

            result = await git_process_image("https://example.com/people.jpg", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "two people walking"
            assert result["french_description"] == "deux personnes qui marchent"
            assert result["generation_time"] >= 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_base64_success(self, mocker):
            """Test process_image avec une image base64 valide."""
            mock_raw_image = MagicMock()
            mocker.patch("backend.models.model3.git_large.base64.b64decode", return_value=b"fake_bytes")
            mocker.patch("backend.models.model3.git_large.Image.open", return_value=mock_raw_image)
            mock_raw_image.convert.return_value = mock_raw_image

            mock_processor = MagicMock()
            mock_model = MagicMock()
            mock_processor.return_value.pixel_values = MagicMock()
            mock_model.generate.return_value = MagicMock()
            mock_processor.batch_decode.return_value = ["a mountain landscape"]

            mocker.patch(
                "backend.models.model3.git_large.GoogleTranslator",
                return_value=MagicMock(translate=MagicMock(return_value="un paysage de montagne"))
            )

            result = await git_process_image("aGVsbG8=", mock_processor, mock_model)

            assert result["success"] is True
            assert result["english_description"] == "a mountain landscape"
            assert result["french_description"] == "un paysage de montagne"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_process_image_error(self, mocker):
            """Test process_image retourne un dict avec 'error' en cas d'exception."""
            mocker.patch(
                "backend.models.model3.git_large.requests.get",
                side_effect=Exception("Image introuvable")
            )

            mock_processor = MagicMock()
            mock_model = MagicMock()

            result = await git_process_image("https://example.com/missing.jpg", mock_processor, mock_model)

            assert "error" in result
            assert "Image introuvable" in result["error"]

    class TestDescribeImageWithGitLarge:

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_returns_results_list(self, mocker):
            """Test que describe_image_with_git_large retourne une liste de résultats."""
            mock_result = {
                "success": True,
                "english_description": "a mountain",
                "french_description": "une montagne",
                "generation_time": 0.8
            }
            mocker.patch(
                "backend.models.model3.git_large.process_image",
                new=AsyncMock(return_value=mock_result)
            )

            result = await describe_image_with_git_large(["img1", "img2"])

            assert "results" in result
            assert len(result["results"]) == 2

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_empty_list(self, mocker):
            """Test que describe_image_with_git_large retourne une liste vide."""
            result = await describe_image_with_git_large([])

            assert result == {"results": []}
