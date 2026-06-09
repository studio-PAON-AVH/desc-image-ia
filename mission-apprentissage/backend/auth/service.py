import jwt
import os
import secrets
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
from ..core.database.config import User
from .repository import (
    find_user_by_email,
    find_user_by_id,
    create_refresh_token_record,
    find_valid_refresh_token,
    revoke_refresh_token_record,
)

load_dotenv()
hasher = PasswordHash.recommended()

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


async def create_refresh_token(email: str, db: AsyncSession) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
    user = await find_user_by_email(db, email)
    await create_refresh_token_record(db, token, user.id, expires_at)
    return token


async def validate_refresh_token(token: str, db: AsyncSession) -> str | None:
    refresh = await find_valid_refresh_token(db, token)
    if not refresh:
        return None
    user = await find_user_by_id(db, refresh.user_id)
    return user.email if user else None


async def revoke_refresh_token(token: str, db: AsyncSession) -> None:
    await revoke_refresh_token_record(db, token)


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hasher.verify(plain_password, hashed_password)


async def get_user(db: AsyncSession, email: str) -> User | None:
    return await find_user_by_email(db, email)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=int(15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return encoded_jwt
