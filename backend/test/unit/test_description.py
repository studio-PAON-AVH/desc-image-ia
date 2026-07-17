import zipfile
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.descriptions.service import get_validated_description, add_descriptions


def make_epub_zip(tmp_path, image_name="cat.jpg", add_html=True):
    """Crée un fichier epub (zip) minimal dans tmp_path et retourne son chemin."""
    epub_path = str(tmp_path / "book.epub")
    html_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<img src="images/{image_name}" alt=""/>
</body>
</html>""".encode("utf-8")

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        if add_html:
            zf.writestr("chapter1.xhtml", html_content)
        zf.writestr(f"images/{image_name}", b"fake_image_bytes")

    return epub_path


class TestDescriptionService:
    class TestGetValidatedDescription:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_validated_description_success(self, session):
            """Rows trouvés → dict {image_file_name: description_text}."""
            mock_img = MagicMock()
            mock_img.image_file_name = "cat.jpg"
            mock_desc = MagicMock()
            mock_desc.description_text = "Un chat"

            mock_result = MagicMock()
            mock_result.all.return_value = [(MagicMock(), mock_img, mock_desc)]
            session.execute = AsyncMock(return_value=mock_result)

            result = await get_validated_description(session, "task-123")

            assert result == {"cat.jpg": "Un chat"}

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_validated_description_empty(self, session):
            """Aucune ligne → dict vide {}."""
            mock_result = MagicMock()
            mock_result.all.return_value = []
            session.execute = AsyncMock(return_value=mock_result)

            result = await get_validated_description(session, "task-123")

            assert result == {}

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_get_validated_description_db_error(self, session):
            """Erreur DB → exception propagée."""
            session.execute = AsyncMock(side_effect=Exception("DB error"))

            with pytest.raises(Exception, match="DB error"):
                await get_validated_description(session, "task-123")

    class TestAddDescriptions:
        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_add_descriptions_success(self, mocker, tmp_path, session):
            """Epub valide avec HTML/XHTML et image → alt ajouté, output_path retourné."""
            epub_path = make_epub_zip(tmp_path, image_name="cat.jpg")
            output_path = str(tmp_path / "book_modified.epub")

            mocker.patch(
                "backend.descriptions.service.get_validated_description",
                new=AsyncMock(return_value={"cat.jpg": "Un chat"}),
            )

            result = await add_descriptions(session, "task-123", epub_path, output_path)

            assert result == output_path
            with zipfile.ZipFile(output_path) as zf:
                content = zf.read("chapter1.xhtml").decode("utf-8")
            assert 'alt="Un chat"' in content

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_add_descriptions_no_html(self, session, tmp_path):
            """Epub sans fichier .html/.xhtml → ValueError."""
            epub_path = make_epub_zip(tmp_path, add_html=False)
            output_path = str(tmp_path / "output.epub")

            with pytest.raises(ValueError, match="HTML ou XHTML"):
                await add_descriptions(session, "task-123", epub_path, output_path)

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_add_descriptions_no_descriptions(self, mocker, tmp_path, session):
            """Descriptions vides → epub réécrit sans modification des items."""
            epub_path = make_epub_zip(tmp_path, image_name="cat.jpg")
            output_path = str(tmp_path / "book_modified.epub")

            mocker.patch(
                "backend.descriptions.service.get_validated_description",
                new=AsyncMock(return_value={}),
            )

            result = await add_descriptions(session, "task-123", epub_path, output_path)

            assert result == output_path
            assert (tmp_path / "book_modified.epub").exists()

        @pytest.mark.unit
        @pytest.mark.asyncio
        async def test_add_descriptions_db_error(self, mocker, tmp_path, session):
            """Erreur DB dans get_validated_description → exception propagée."""
            epub_path = make_epub_zip(tmp_path, image_name="cat.jpg")
            output_path = str(tmp_path / "output.epub")

            mocker.patch(
                "backend.descriptions.service.get_validated_description",
                new=AsyncMock(side_effect=Exception("DB crash")),
            )

            with pytest.raises(Exception, match="DB crash"):
                await add_descriptions(session, "task-123", epub_path, output_path)
