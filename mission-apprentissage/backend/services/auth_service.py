import jwt
import os
import secrets
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
from sqlalchemy import select
from ..database import User
from ..redis.redis import redis_server_dev

load_dotenv()
hasher = PasswordHash.recommended()
r = redis_server_dev()

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_refresh_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    r.set(f"refresh:{token}", email, ex=REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    return token


def validate_refresh_token(token: str) -> str | None:
    email = r.get(f"refresh:{token}")
    if email is None:
        return None
    return email.decode() if isinstance(email, bytes) else email


def revoke_refresh_token(token: str) -> None:
    r.delete(f"refresh:{token}")

def hash_password(password: str) -> str:
    return hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hasher.verify(plain_password, hashed_password)

async def get_user(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

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