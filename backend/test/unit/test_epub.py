import pytest
import base64
import httpx
from unittest.mock import AsyncMock, MagicMock
from backend.epub.service import (
    get_image_describe,
    stream_image_describe,
    slice_to_image_descriptions,
    extract_images_epub,
    describe_images_epub,
)
from backend.epub.middleware import already_exists as epub_already_exists


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
                "file_name",
                "salesforce_blip",
                "florence2",
                "git_large",
            }
            assert result["images"]["image_1"].keys() == {
                "index",
                "file_name",
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
        async def test_get_image_describe_batching(self, mocker):
            """Test de la logique de batching dans get_image_describe."""
            import os

            # On épingle BATCH_SIZE=5 : ce test vérifie la maths de batching,
            # indépendamment du défaut (désormais 1 = rendu image par image).
            mocker.patch.dict(os.environ, {"BATCH_SIZE": "5"})
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

    class TestStreamImageDescribe:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_yields_one_event_per_batch_model(self, mocker):
            """Le stream yield un event par (batch, modèle) avec les bonnes métadonnées."""
            import os

            # BATCH_SIZE=5 -> les 2 images tiennent dans un seul batch.
            mocker.patch.dict(os.environ, {"BATCH_SIZE": "5"})
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {
                    "results": [
                        {"french_description": "Un chat"},
                        {"french_description": "Un chien"},
                    ]
                },
            )
            mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img_list = [
                base64.b64encode(b"img1").decode("utf-8"),
                base64.b64encode(b"img2").decode("utf-8"),
            ]

            events = [evt async for evt in stream_image_describe(img_list)]

            # 1 batch (batch_size défaut 5 >= 2 images) × 3 modèles
            assert len(events) == 3
            assert {e["model_key"] for e in events} == {
                "salesforce_blip",
                "florence2",
                "git_large",
            }
            assert all(e["batch_idx"] == 0 for e in events)
            assert all(e["total_images"] == 2 for e in events)
            assert all(e["result"].get("results") for e in events)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_failing_model_does_not_block_others(self, mocker):
            """Un modèle en échec yield quand même son event, sans bloquer les autres."""
            mocker.patch(
                "httpx.AsyncClient.post", side_effect=httpx.RequestError("network down")
            )

            img_list = [base64.b64encode(b"img1").decode("utf-8")]

            events = [evt async for evt in stream_image_describe(img_list)]

            assert len(events) == 3
            assert all(e["result"].get("success") is False for e in events)
            # rien à persister pour un slice en échec
            for e in events:
                assert (
                    slice_to_image_descriptions(
                        e["batch_idx"], e["batch_size"], e["model_key"], e["result"], 1
                    )
                    == {}
                )

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_batch_size_one_yields_per_image(self, mocker):
            """Avec BATCH_SIZE=1, chaque image part dans son propre appel HTTP."""
            import os

            mocker.patch.dict(os.environ, {"BATCH_SIZE": "1"})
            mocker_response = AsyncMock(
                status_code=200,
                json=lambda: {"results": [{"french_description": "desc"}]},
            )
            post_mock = mocker.patch("httpx.AsyncClient.post", return_value=mocker_response)

            img_list = [
                base64.b64encode(f"img{i}".encode()).decode("utf-8") for i in range(3)
            ]

            events = [evt async for evt in stream_image_describe(img_list)]

            # 3 images × 3 modèles = 9 appels / events, un batch par image
            assert post_mock.call_count == 9
            assert len(events) == 9
            assert all(e["batch_size"] == 1 for e in events)
            # chaque image (batch_idx 0,1,2) est vue par les 3 modèles
            from collections import Counter

            per_batch = Counter(e["batch_idx"] for e in events)
            assert per_batch == {0: 3, 1: 3, 2: 3}

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_respects_max_concurrent_per_model(self, mocker):
            """Le sémaphore plafonne les requêtes en vol PAR MODÈLE (1 par défaut)."""
            import asyncio
            import os
            from collections import defaultdict

            mocker.patch.dict(
                os.environ, {"BATCH_SIZE": "1", "MAX_CONCURRENT_PER_MODEL": "1"}
            )

            current = defaultdict(int)
            peak = defaultdict(int)

            async def fake_post(url, json=None):
                current[url] += 1
                peak[url] = max(peak[url], current[url])
                await asyncio.sleep(0.01)
                current[url] -= 1
                return AsyncMock(
                    status_code=200, json=lambda: {"results": [{"french_description": "d"}]}
                )

            mocker.patch("httpx.AsyncClient.post", side_effect=fake_post)

            img_list = [
                base64.b64encode(f"img{i}".encode()).decode("utf-8") for i in range(4)
            ]

            events = [evt async for evt in stream_image_describe(img_list)]

            assert len(events) == 12  # 4 images × 3 modèles
            # 3 URLs distinctes (une par modèle), jamais plus d'1 requête en vol chacune
            assert len(peak) == 3
            assert all(p <= 1 for p in peak.values())

    class TestSliceToImageDescriptions:
        @pytest.mark.unit
        def test_applies_batch_offset(self):
            """Les index globaux tiennent compte de batch_idx * batch_size."""
            result = {"results": [{"french_description": "a"}, {"french_description": "b"}]}
            out = slice_to_image_descriptions(1, 2, "florence2", result, total_images=4)
            assert set(out.keys()) == {2, 3}

        @pytest.mark.unit
        def test_trims_out_of_range_indices(self):
            """Les résultats au-delà de total_images sont ignorés."""
            result = {"results": [{"french_description": "a"}, {"french_description": "b"}]}
            out = slice_to_image_descriptions(1, 2, "git_large", result, total_images=3)
            assert set(out.keys()) == {2}

        @pytest.mark.unit
        def test_empty_for_failed_result(self):
            """Un résultat sans 'results' donne un mapping vide."""
            assert slice_to_image_descriptions(0, 5, "git_large", {"success": False}, 2) == {}
            assert slice_to_image_descriptions(0, 5, "git_large", None, 2) == {}

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
