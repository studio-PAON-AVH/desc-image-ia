from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database.config import User, RefreshToken, Task
from sqlalchemy.orm import selectinload


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def find_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def user_exists_by_email(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first() is not None


async def create_user(
    db: AsyncSession, username: str, email: str, password_hash: str, role: str = "user"
) -> User:
    date_now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        created_at=date_now,
        updated_at=date_now,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def create_refresh_token_record(
    db: AsyncSession, token: str, user_id: int, expires_at: datetime
) -> RefreshToken:
    record = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(record)
    await db.commit()
    return record


async def find_valid_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    return result.scalars().first()


async def revoke_refresh_token_record(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(RefreshToken).filter(RefreshToken.token == token))
    record = result.scalars().first()
    if record:
        record.revoked = True
        await db.commit()


async def find_tasks_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Task).options(selectinload(Task.epubs)).where(Task.user_id == user_id)
    )
    return result.scalars().all()
