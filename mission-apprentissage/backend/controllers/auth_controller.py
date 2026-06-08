from datetime import datetime, timedelta, timezone
import os
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import User, get_session
from ..services.auth_service import create_access_token, authenticate_user, hash_password, create_refresh_token, validate_refresh_token, revoke_refresh_token
from ..middlewares.auth_middleware import get_current_user, is_admin

class RefreshRequest(BaseModel):
    refresh_token: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
    
async def create_new_user(db: Annotated[AsyncSession, Depends(get_session)], user_data: UserCreate) -> dict:
    # Vérification si l'email existe déjà
    existing_user = await db.execute(select(User).filter(User.email == user_data.email))
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email est déjà utilisé."
        )
    hashed_password = hash_password(user_data.password)
    date_now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_user = User(username=user_data.username, email=user_data.email, password_hash=hashed_password, created_at=date_now, updated_at=date_now)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    access_token = create_access_token(data={"sub": new_user.email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(new_user.email)
    return {
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"}

async def create_admin_user(db: Annotated[AsyncSession, Depends(get_session)], current_user: Annotated[User, Depends(get_current_user)], user_data: UserCreate) -> dict:
    is_admin(current_user)
    # Vérification si l'email existe déjà
    existing_user = await db.execute(select(User).filter(User.email == user_data.email))
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email est déjà utilisé."
        )
    hashed_password = hash_password(user_data.password)
    date_now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_user = User(username=user_data.username, email=user_data.email, password_hash=hashed_password, role="admin", created_at=date_now, updated_at=date_now)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    access_token = create_access_token(data={"sub": new_user.email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(new_user.email)
    return {
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"}

async def login_for_access_token(form_data: UserLogin, db: Annotated[AsyncSession, Depends(get_session)]):
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user.email)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

async def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }
    
async def refresh_access_token(body: RefreshRequest):
    email = validate_refresh_token(body.refresh_token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou expiré")
    revoke_refresh_token(body.refresh_token)
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    new_access_token = create_access_token(data={"sub": email}, expires_delta=access_token_expires)
    new_refresh_token = create_refresh_token(email)
    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


async def logout(body: RefreshRequest):
    revoke_refresh_token(body.refresh_token)
    return {"detail": "Déconnecté avec succès"}


async def get_current_user_tasks(current_user: Annotated[User, Depends(get_current_user)]):
    return {
        "tasks": [
            {
                "task_id_redis": task.task_id_redis,
                "epubs": [
                    {
                        "file_name": epub.file_name,
                        "upload_date": epub.upload_date,
                        "status": epub.status,
                    }
                    for epub in task.epubs
                ],
                "status": task.status,
                "total_images": task.total_images,
                "processed_images": task.processed_images,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
            }
            for task in current_user.task
        ]
    }