import pytest
import base64
import httpx
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock
from backend.utils import ImageRequest
from backend.epub.service import (
    get_image_describe,
    extract_images_epub,
    describe_images_epub,
    save_epub,
    save_task,
    save_images,
    save_image_descriptions,
    update_task_status,
)
from backend.core.database.config import Images, ImageDescription
from backend.epub.middleware import already_exists as epub_already_exists

load_dotenv()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    return user


@pytest.fixture
def mock_upload():
    upload = MagicMock()
    upload.filename = "test.epub"
    upload.file = MagicMock()
    upload.read = AsyncMock(return_value=b"PK\x03\x04" + b"\x00" * 100)
    return upload


@pytest.fixture
def session(mocker):
    mock = mocker.MagicMock()
    mock.add = mocker.MagicMock(return_value=None)
    mock.commit = mocker.AsyncMock(return_value=None)
    mock.refresh = mocker.AsyncMock(return_value=None)
    mock.execute = mocker.AsyncMock(return_value=None)
    return mock


class TestEpubService:
    class TestGetImageDescribe:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_correct_structure(self, mocker):
            """Test de la structure des descriptions retournées par les modèles IA."""
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.5,
                        },
                        {
                            "success": True,
                            "english_description": "A dog",
                            "french_description": "Un chien",
                            "generation_time": 0.5,
                        },
                    ]
                },
            )
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            img2_b64 = base64.b64encode(b"fake_image_data_2").decode("utf-8")
            img_list = [img1_b64, img2_b64]

            result = await get_image_describe(img_list)

            assert isinstance(result, dict)
            assert "images" in result
            assert "total_images" in result
            assert "time" in result
            assert result["images"]["image_0"].keys() == {
                "index",
                "salesforce_blip",
                "florence2",
                "git_large",
            }
            assert result["images"]["image_1"].keys() == {
                "index",
                "salesforce_blip",
                "florence2",
                "git_large",
            }
            assert isinstance(result["time"], float)
            assert result["time"] >= 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_return_not_correct_structure(self, mocker):
            """Test que get_image_describe retourne toujours la bonne structure même si le modèle répond mal."""
            mocker_response = AsyncMock(status_code=200, json=lambda: {"wrong_key": "wrong_value"})
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            img_list = [img1_b64]
            result = await get_image_describe(img_list)
            assert isinstance(result, dict)
            assert "images" in result
            assert "total_images" in result
            assert "time" in result
            assert "wrong_key" not in result

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_error_handling(self, mocker):
            """Test de la gestion des erreurs dans get_image_describe."""

            mocker.patch("httpx.AsyncClient.post", side_effect=Exception("Service unavailable"))

            img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            img_list = [img1_b64]

            result = await get_image_describe(img_list)

            assert isinstance(result, dict)
            assert "images" in result
            assert "total_images" in result
            assert "time" in result

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_request_error(self, mocker):
            """Test de la gestion des erreurs de requête dans get_image_describe."""
            mocker.patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Request error"))

            img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            result = await get_image_describe([img1_b64])

            assert "images" in result
            assert "total_images" in result
            assert "time" in result
            assert result["total_images"] == 1
            image = result["images"]["image_0"]
            assert image["salesforce_blip"] is None
            assert image["florence2"] is None
            assert image["git_large"] is None

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_empty_list(self, mocker):
            """Test de get_image_describe avec une liste d'images vide."""
            mocker_response = AsyncMock(status_code=200, json=lambda: {"results": []})
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img_list = []
            result = await get_image_describe(img_list)

            assert isinstance(result, dict)
            assert result["images"] == {}
            assert result["total_images"] == 0

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_call_models(self, mocker):
            """Garantie que get_image_describe appelle les modèles externes."""
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.3,
                        }
                    ]
                },
            )
            post_mock = mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img_1_bs64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            img_2_bs64 = base64.b64encode(b"fake_image_data_2").decode("utf-8")
            img_bs64_list = [img_1_bs64, img_2_bs64]

            result = await get_image_describe(img_bs64_list)
            assert "images" in result
            assert post_mock.call_count == 3

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_batching(self, mocker):
            """Test de la logique de batching dans get_image_describe."""
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": f"desc {i}",
                            "french_description": f"desc fr {i}",
                            "generation_time": 0.4,
                        }
                        for i in range(5)
                    ]
                },
            )
            post_mock = mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img_bs64_list = [
                base64.b64encode(f"fake_image_data_{i}".encode()).decode("utf-8") for i in range(12)
            ]
            result = await get_image_describe(img_bs64_list)

            assert post_mock.call_count == 9
            assert "images" in result

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_calls_all_models(self, mocker):
            """Test que get_image_describe appelle tous les modèles pour chaque batch."""
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": "desc",
                            "french_description": "desc fr",
                            "generation_time": 0.4,
                        }
                    ]
                },
            )

            img_bs64_list = [
                base64.b64encode(f"fake_image_data_{i}".encode()).decode("utf-8") for i in range(7)
            ]

            post_mock = mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            result = await get_image_describe(img_bs64_list)

            assert post_mock.call_count == 6
            assert "images" in result

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_model_returns_error(self, mocker):
            """Test la gestion des erreurs retournées par les modèles dans get_image_describe."""
            mocker_response = AsyncMock(status_code=500, text="Internal Server Error")

            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img1_b64 = base64.b64encode(b"fake_image_data_1").decode("utf-8")
            img_list = [img1_b64]

            result = await get_image_describe(img_list)

            assert isinstance(result, dict)
            assert "images" in result
            assert "total_images" in result
            assert result["total_images"] == 1
            assert result["images"]["image_0"]["salesforce_blip"] is None

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_batch_size_value_error(self, mocker):
            """Test la gestion d'une valeur de batch_size invalide dans get_image_describe."""
            import os

            mocker.patch.dict(os.environ, {"BATCH_SIZE": "-1"})
            img_bs64_list = [base64.b64encode(b"fake_image_data").decode("utf-8")]

            with pytest.raises(ValueError):
                await get_image_describe(img_bs64_list)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_batch_size_invalid_string(self, mocker):
            """Test que BATCH_SIZE non numérique utilise le fallback à 5."""
            import os

            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": "desc",
                            "french_description": "desc fr",
                            "generation_time": 0.4,
                        }
                    ]
                },
            )
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)
            mocker.patch.dict(os.environ, {"BATCH_SIZE": "abc"})

            img_bs64_list = [base64.b64encode(b"fake_image_data").decode("utf-8")]
            result = await get_image_describe(img_bs64_list)

            assert "images" in result
            assert result["total_images"] == 1

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_image_describe_batch_max_invalid_string(self, mocker):
            """Test que BATCH_MAX non numérique utilise le fallback à 200."""
            import os

            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {
                            "success": True,
                            "english_description": "desc",
                            "french_description": "desc fr",
                            "generation_time": 0.4,
                        }
                    ]
                },
            )
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)
            mocker.patch.dict(os.environ, {"BATCH_MAX": "abc"})

            img_bs64_list = [base64.b64encode(b"fake_image_data").decode("utf-8")]
            result = await get_image_describe(img_bs64_list)

            assert "images" in result
            assert result["total_images"] == 1

    class TestImageRequest:
        @pytest.mark.unit
        def test_request_image_request_valid(self):
            """Test de la validation de ImageRequest avec des images valides."""
            img_local = ["fake_image_data_1", "fake_image_data_2"]
            request = ImageRequest(images=img_local)
            assert request.images == img_local

        @pytest.mark.unit
        def test_request_image_request_invalid(self):
            """Test de la validation de ImageRequest avec des images invalides."""
            img_local = "not_a_list"
            with pytest.raises(Exception):
                ImageRequest(images=img_local)

        @pytest.mark.unit
        def test_request_image_request_none(self):
            """Test avec None au lieu d'une liste."""
            with pytest.raises(Exception):
                ImageRequest(images=None)

        @pytest.mark.unit
        def test_request_image_request_empty(self):
            """Test avec une chaîne au lieu d'une liste."""
            img_local = ["", ""]
            request = ImageRequest(images=img_local)
            assert request.images == img_local

    class TestExtractImagesEpub:
        @pytest.mark.unit
        def test_extract_images_epub_valid(self, mocker, tmp_path):
            """Test de l'extraction d'images d'un EPUB valide."""
            mock_item = mocker.Mock()
            mock_item.file_name = "images/cat.jpg"
            mock_item.get_content.return_value = b"fake_image_bytes"

            mock_book = mocker.Mock()
            mock_book.get_items_of_type.return_value = [mock_item, mock_item]

            mocker.patch("backend.epub.service.epub.read_epub", return_value=mock_book)

            result_paths, result_dir = extract_images_epub(
                "some/path/to/book.epub", output_dir=str(tmp_path)
            )

            assert isinstance(result_paths, list)
            assert len(result_paths) == 2
            assert all(p.endswith("cat.jpg") for p in result_paths)

        @pytest.mark.unit
        def test_extract_images_epub_invalid(self, mocker):
            """Test de l'extraction d'images d'un EPUB invalide (exception propagée)."""
            mocker.patch(
                "backend.epub.service.epub.read_epub", side_effect=Exception("Invalid EPUB file")
            )

            with pytest.raises(Exception):
                extract_images_epub("invalid/path/to/book.epub")

        @pytest.mark.unit
        def test_extract_images_epub_empty(self, mocker):
            """Test de l'extraction d'images d'un EPUB sans images."""
            mock_book = mocker.Mock()
            mock_book.get_items_of_type.return_value = []
            mocker.patch("backend.epub.service.epub.read_epub", return_value=mock_book)

            result_paths, result_dir = extract_images_epub("some/path/to/book.epub")

            assert isinstance(result_paths, list)
            assert len(result_paths) == 0
            assert result_dir is None

        @pytest.mark.unit
        def test_extract_images_epub_error(self, mocker):
            """Test de la gestion des erreurs lors de l'extraction d'images d'un EPUB."""
            mocker.patch("backend.epub.service.epub.read_epub", side_effect=Exception("Read error"))

            with pytest.raises(Exception):
                extract_images_epub("some/path/to/book.epub")

        @pytest.mark.unit
        def test_extract_images_epub_creates_temp_dir(self, mocker):
            """Test que extract_images_epub crée un dossier temporaire quand output_dir=None."""
            mock_item = mocker.Mock()
            mock_item.file_name = "images/cat.jpg"
            mock_item.get_content.return_value = b"fake_image_bytes"

            mock_book = mocker.Mock()
            mock_book.get_items_of_type.return_value = [mock_item]

            mocker.patch("backend.epub.service.epub.read_epub", return_value=mock_book)
            mock_mkdtemp = mocker.patch(
                "backend.epub.service.tempfile.mkdtemp", return_value="/tmp/epub_test"
            )
            mocker.patch("builtins.open", mocker.mock_open())

            result_paths, result_dir = extract_images_epub(
                "some/path/to/book.epub"
            )  # pas de output_dir

            mock_mkdtemp.assert_called_once_with(prefix="epub_images_")
            assert result_dir == "/tmp/epub_test"

    class TestDescribeImagesEpub:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_valid(self, mocker, tmp_path):
            """Test de la description d'images d'un EPUB avec des données valides."""
            img_file = tmp_path / "cat.jpg"
            img_file.write_bytes(b"fake_image_bytes")

            mocker.patch(
                "backend.epub.service.extract_images_epub", return_value=([str(img_file)], None)
            )

            expected = {
                "images": {
                    "image_0": {
                        "index": 0,
                        "salesforce_blip": {
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.5,
                        },
                        "florence2": {
                            "english_description": "A feline",
                            "french_description": "Un félin",
                            "generation_time": 0.4,
                        },
                        "git_large": {
                            "english_description": "A domestic cat",
                            "french_description": "Un chat domestique",
                            "generation_time": 0.6,
                        },
                    }
                },
                "total_images": 1,
                "time": 1.5,
            }
            mocker.patch(
                "backend.epub.service.get_image_describe",
                new_callable=AsyncMock,
                return_value=expected,
            )

            result = await describe_images_epub("some/path/to/book.epub")

            assert isinstance(result, dict)
            assert "images" in result
            assert result["total_images"] == 1
            assert result["images"]["image_0"]["index"] == 0
            assert result["images"]["image_0"]["salesforce_blip"]["english_description"] == "A cat"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_no_images(self, mocker):
            """Test quand l'EPUB ne contient pas d'images."""
            mocker.patch("backend.epub.service.extract_images_epub", return_value=([], None))

            result = await describe_images_epub("some/path/to/book.epub")

            assert isinstance(result, dict)
            assert "error" in result

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_extract_error(self, mocker):
            """Test quand extract_images_epub lève une exception."""
            mocker.patch(
                "backend.epub.service.extract_images_epub", side_effect=Exception("EPUB illisible")
            )

            with pytest.raises(Exception):
                await describe_images_epub("some/path/to/book.epub")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_model_error(self, mocker, tmp_path):
            """Test quand get_image_describe échoue."""
            img_file = tmp_path / "cat.jpg"
            img_file.write_bytes(b"fake_image_bytes")

            mocker.patch(
                "backend.epub.service.extract_images_epub", return_value=([str(img_file)], None)
            )
            mocker.patch(
                "backend.epub.service.get_image_describe",
                new_callable=AsyncMock,
                side_effect=Exception("Model error"),
            )

            with pytest.raises(Exception):
                await describe_images_epub("some/path/to/book.epub")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_partial_success(self, mocker, tmp_path):
            """Test quand un modèle échoue (florence2=None)."""
            img_file = tmp_path / "cat.jpg"
            img_file.write_bytes(b"fake_image_bytes")

            mocker.patch(
                "backend.epub.service.extract_images_epub", return_value=([str(img_file)], None)
            )

            expected = {
                "images": {
                    "image_0": {
                        "index": 0,
                        "salesforce_blip": {
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.5,
                        },
                        "florence2": None,
                        "git_large": {
                            "english_description": "A domestic cat",
                            "french_description": "Un chat domestique",
                            "generation_time": 0.6,
                        },
                    }
                },
                "total_images": 1,
                "time": 1.5,
            }
            mocker.patch(
                "backend.epub.service.get_image_describe",
                new_callable=AsyncMock,
                return_value=expected,
            )

            result = await describe_images_epub("some/path/to/book.epub")

            assert isinstance(result, dict)
            assert "images" in result
            assert result["total_images"] == 1
            assert result["images"]["image_0"]["index"] == 0
            assert result["images"]["image_0"]["salesforce_blip"]["english_description"] == "A cat"
            assert result["images"]["image_0"]["florence2"] is None

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_describe_images_epub_cleanup_temp_folder(self, mocker, tmp_path):
            """Test que le dossier temporaire est supprimé après describe_images_epub."""
            img_file = tmp_path / "cat.jpg"
            img_file.write_bytes(b"fake_image_bytes")

            temp_dir = str(tmp_path)
            mocker.patch(
                "backend.epub.service.extract_images_epub", return_value=([str(img_file)], temp_dir)
            )
            mock_rmtree = mocker.patch("backend.epub.service.shutil.rmtree")
            mocker.patch(
                "backend.epub.service.get_image_describe",
                new_callable=AsyncMock,
                return_value={"images": {}, "total_images": 1, "time": 0.1},
            )

            await describe_images_epub("some/path/to/book.epub")

            mock_rmtree.assert_called_once_with(temp_dir)

    class TestSaveEpub:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_epub_success(self, session):
            """Test de la sauvegarde d'un EPUB dans la base de données."""
            result = await save_epub(session, task_id=1, file_name="test.epub")

            assert session.add.called
            assert result.file_name == "test.epub"

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_epub_commit_error(self, session):
            """Test de la gestion des erreurs lors du commit."""
            session.commit.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await save_epub(session, task_id=1, file_name="test.epub")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_epub_refresh_failure(self, session):
            """Test de la gestion des erreurs lors du rafraîchissement de l'instance après commit."""
            session.refresh.side_effect = Exception("Refresh error")

            with pytest.raises(Exception):
                await save_epub(session, task_id=1, file_name="test.epub")

    class TestSaveTask:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_task_success(self, session):
            """Test de la sauvegarde d'un EPUB dans la base de données."""
            result = await save_task(session, task_id_redis="1", user_id=1)

            assert session.add.called
            assert result.task_id_redis == "1"
            assert result.user_id == 1

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_task_commit_error(self, session):
            """Test de la gestion des erreurs lors du commit."""
            session.commit.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await save_task(session, task_id_redis="1", user_id=1)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_task_refresh_failure(self, session):
            """Test de la gestion des erreurs lors du rafraîchissement de l'instance après commit."""
            session.refresh.side_effect = Exception("Refresh error")

            with pytest.raises(Exception):
                await save_task(session, task_id_redis="1", user_id=1)

    class TestSaveImages:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_images_success(self, session):
            """Test de la sauvegarde des images extraites d'un EPUB dans la base de données."""
            img_paths = ["/path/to/fake_image_path1.jpg", "/path/to/fake_image_path2.jpg"]

            result = await save_images(session, task_id=1, epub_id=1, image_paths=img_paths)

            assert session.add.call_count == len(img_paths)
            assert session.commit.called
            assert session.refresh.call_count == len(img_paths)
            assert len(result) == len(img_paths)
            assert result[0].task_id == 1
            assert result[0].epub_id == 1
            assert result[0].image_file_name == "fake_image_path1.jpg"
            assert result[0].image_position_in_epub == 0
            assert result[1].image_position_in_epub == 1

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_images_commit_error(self, session):
            """Test de la gestion des erreurs lors du commit."""
            session.commit.side_effect = Exception("Database error")
            img_paths = ["/path/to/fake_image_path1.jpg", "/path/to/fake_image_path2.jpg"]

            with pytest.raises(Exception):
                await save_images(session, task_id=1, epub_id=1, image_paths=img_paths)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_images_refresh_failure(self, session):
            """Test de la gestion des erreurs lors du rafraîchissement de l'instance après commit."""
            session.refresh.side_effect = Exception("Refresh error")
            img_paths = ["/path/to/fake_image_path1.jpg", "/path/to/fake_image_path2.jpg"]

            with pytest.raises(Exception):
                await save_images(session, task_id=1, epub_id=1, image_paths=img_paths)

    class TestSaveImageDescriptions:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_image_descriptions_success(self, session):
            """Test de la sauvegarde des descriptions d'images dans la base de données."""
            img_list = [
                Images(
                    task_id=1,
                    epub_id=1,
                    image_file_name="fake_image_path1.jpg",
                    image_position_in_epub=0,
                ),
                Images(
                    task_id=1,
                    epub_id=1,
                    image_file_name="fake_image_path2.jpg",
                    image_position_in_epub=1,
                ),
            ]
            results = {
                "images": {
                    "image_0": {
                        "salesforce_blip": {
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.5,
                        },
                        "florence2": {
                            "english_description": "A feline",
                            "french_description": "Un félin",
                            "generation_time": 0.4,
                        },
                        "git_large": {
                            "english_description": "A domestic cat",
                            "french_description": "Un chat domestique",
                            "generation_time": 0.6,
                        },
                    },
                    "image_1": {
                        "salesforce_blip": {
                            "english_description": "A dog",
                            "french_description": "Un chien",
                            "generation_time": 0.5,
                        },
                        "florence2": {
                            "english_description": "A canine",
                            "french_description": "Un canidé",
                            "generation_time": 0.4,
                        },
                        "git_large": {
                            "english_description": "A domestic dog",
                            "french_description": "Un chien domestique",
                            "generation_time": 0.6,
                        },
                    },
                },
                "total_images": 2,
                "time": 1.5,
            }
            model_ia_mapping = {"salesforce_blip": 1, "florence2": 2, "git_large": 3}

            await save_image_descriptions(
                session, images=img_list, results=results, model_ia_mapping=model_ia_mapping
            )

            # 2 images × 3 modèles = 6 descriptions
            assert session.add.call_count == len(img_list) * len(model_ia_mapping)
            assert session.commit.called

            # Vérifier le contenu du premier objet ajouté
            first_desc = session.add.call_args_list[0][0][0]
            assert isinstance(first_desc, ImageDescription)
            assert first_desc.description_text == "Un chat"
            assert first_desc.model_ia_id == 1
            assert first_desc.is_written_by_ai == True

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_save_image_descriptions_commit_error(self, session):
            """Test de la gestion des erreurs lors du commit."""
            session.commit.side_effect = Exception("Database error")
            img_list = [
                Images(
                    task_id=1,
                    epub_id=1,
                    image_file_name="fake_image_path1.jpg",
                    image_position_in_epub=0,
                )
            ]
            results = {
                "images": {
                    "image_0": {
                        "salesforce_blip": {
                            "english_description": "A cat",
                            "french_description": "Un chat",
                            "generation_time": 0.5,
                        },
                        "florence2": {
                            "english_description": "A feline",
                            "french_description": "Un félin",
                            "generation_time": 0.4,
                        },
                        "git_large": {
                            "english_description": "A domestic cat",
                            "french_description": "Un chat domestique",
                            "generation_time": 0.6,
                        },
                    }
                },
                "total_images": 1,
                "time": 1.5,
            }
            model_ia_mapping = {"salesforce_blip": 1, "florence2": 2, "git_large": 3}

            with pytest.raises(Exception):
                await save_image_descriptions(
                    session, images=img_list, results=results, model_ia_mapping=model_ia_mapping
                )

    class TestUpdateTaskStatus:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_update_task_status_success(self, session):
            """Test de la mise à jour du statut d'une tâche."""
            await update_task_status(session, db_task_id=1, status="completed")

            assert session.execute.called
            assert session.commit.called

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_update_task_status_error(self, session):
            """Test de la gestion des erreurs lors de la mise à jour du statut d'une tâche."""
            session.execute.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await update_task_status(session, db_task_id=1, status="completed")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_update_task_status_commit_error(self, session):
            """Test de la gestion des erreurs lors du commit de la mise à jour du statut d'une tâche."""
            session.commit.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await update_task_status(session, db_task_id=1, status="completed")

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_update_task_status_execute_error(self, session):
            """Test de la gestion des erreurs lors de l'exécution de la mise à jour du statut d'une tâche."""
            session.execute.side_effect = Exception("Execution error")

            with pytest.raises(Exception):
                await update_task_status(session, db_task_id=1, status="completed")


class TestEpubMiddleware:
    class TestAlreadyExists:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_already_exists_true(self, session):
            """Test que already_exists retourne True quand le fichier existe en DB."""
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = MagicMock()
            session.execute = AsyncMock(return_value=mock_result)

            result = await epub_already_exists("test.epub", session)

            assert result is True

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_already_exists_false(self, session):
            """Test que already_exists retourne False quand le fichier n'existe pas en DB."""
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = None
            session.execute = AsyncMock(return_value=mock_result)

            result = await epub_already_exists("test.epub", session)

            assert result is False

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_already_exists_db_error(self, session):
            """Test que already_exists propage l'exception en cas d'erreur DB."""
            session.execute = AsyncMock(side_effect=Exception("DB error"))

            with pytest.raises(Exception, match="DB error"):
                await epub_already_exists("test.epub", session)
