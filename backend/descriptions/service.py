import os
import zipfile
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database.config import Task, Images, DescriptionFinale

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")

async def get_validated_description(session: AsyncSession, task_id_redis: str) -> dict[str, str]:
    result = await session.execute(
        select(Task, Images, DescriptionFinale)
        .join(Images, Images.task_id == Task.id)
        .join(DescriptionFinale, DescriptionFinale.image_id == Images.id)
        .where(
            Task.task_id_redis == task_id_redis,
            DescriptionFinale.validated_by_human
        )
    )

    rows = result.all()
    if not rows:
        return {}

    descriptions_map = {}
    for _, img, desc in rows:
        descriptions_map[img.image_file_name] = desc.description_text

    return descriptions_map

async def add_descriptions(
    session: AsyncSession, task_id_redis: str, epub_path: str, output_path: str
) -> str:

    max_uncompressed_size = 500 * 1024 * 1024  # 500 Mo

    with zipfile.ZipFile(epub_path, "r") as zip_ref:
        total_size = sum(info.file_size for info in zip_ref.infolist())
        if total_size > max_uncompressed_size:
            raise ValueError("L'EPUB est trop volumineux une fois décompressé (max 500 Mo)")
        names = zip_ref.namelist()
        html_items = [
            name for name in names if name.endswith((".html", ".xhtml"))
        ]
        if not html_items:
            raise ValueError(f"Aucun fichier HTML ou XHTML trouvé dans l'EPUB : {epub_path}")

        modified_content = {}
        description = await get_validated_description(session, task_id_redis)

        for item_name in html_items:
            content = zip_ref.read(item_name).decode("utf-8")
            soup = BeautifulSoup(content, "html.parser")
            changed = False
            for img in soup.find_all("img"):
                src_text = img.get("src", "")
                if src_text.lower().endswith(IMAGE_EXTENSIONS):
                    img_base_name = os.path.basename(src_text)
                    new_description = description.get(img_base_name)
                    if new_description:
                        img["alt"] = new_description
                        changed = True
            if changed:
                modified_content[item_name] = str(soup).encode("utf-8")
        
        tmp_path = epub_path + ".tmp"
        with zipfile.ZipFile(tmp_path, "w") as zip_write:
            if "mimetype" in names:
                zip_write.writestr(
                    zipfile.ZipInfo("mimetype"), zip_ref.read("mimetype"), compress_type=zipfile.ZIP_STORED
                )
            for name in names:
                if name == "mimetype":
                    continue
                if name in modified_content:
                    zip_write.writestr(name, modified_content[name], compress_type=zipfile.ZIP_DEFLATED)
                else:
                    zip_write.writestr(name, zip_ref.read(name), compress_type=zipfile.ZIP_DEFLATED)

    os.replace(tmp_path, output_path)
    return output_path
    
