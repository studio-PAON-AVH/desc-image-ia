import os
import zipfile
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database.config import Task, Images, DescriptionFinale


async def get_validated_description(session: AsyncSession, task_id_redis: str) -> dict[str, str]:
    result = await session.execute(
        select(Task, Images, DescriptionFinale)
        .join(Images, Images.task_id == Task.id)
        .join(DescriptionFinale, DescriptionFinale.image_id == Images.id)
        .where(
            Task.task_id_redis == task_id_redis,
            (DescriptionFinale.validated_by_human == True),
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
        namelist = zip_ref.namelist()
        opf_path = next((name for name in namelist if name.endswith(".opf")), None)
        if not opf_path:
            raise ValueError("Fichier OPF non trouvé dans l'epub.")
        opf_content = zip_ref.read(opf_path).decode("utf-8")
        all_files = {name: zip_ref.read(name) for name in namelist}

    description = await get_validated_description(session, task_id_redis)

    soup = BeautifulSoup(opf_content, "xml")
    for item in soup.find_all("item"):
        media_type = item.get("media-type", "")
        href = item.get("href", "")
        if media_type.startswith("image/"):
            img_base_name = os.path.basename(href)
            if img_base_name in description:
                item["alt"] = description[img_base_name]

    modified_opf = str(soup).encode("utf-8")
    tpm_path = output_path + ".tmp"
    with zipfile.ZipFile(tpm_path, "w") as zip_write:
        if "mimetype" in all_files:
            zip_write.writestr(
                zipfile.ZipInfo("mimetype"), all_files["mimetype"], compress_type=zipfile.ZIP_STORED
            )
        for name in namelist:
            if name == "mimetype":
                continue
            if name == opf_path:
                zip_write.writestr(name, modified_opf, compress_type=zipfile.ZIP_DEFLATED)
            else:
                zip_write.writestr(name, all_files[name], compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tpm_path, output_path)
    return output_path
