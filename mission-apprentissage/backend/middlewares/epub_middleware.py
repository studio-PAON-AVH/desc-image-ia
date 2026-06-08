from ..database import AsyncSession, Epub
from sqlalchemy import select


async def already_exists(file_name: str, session: AsyncSession) -> bool:
    result = await session.execute(select(Epub).where(Epub.file_name == file_name))
    return result.scalars().first() is not None