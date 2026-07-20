from datetime import timedelta
import os
from typing import Annotated
from fastapi import Depends, HTTPException, Request, Response, status
from .rate_limit import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database.config import User, get_session
from .service import (
    create_access_token,
    authenticate_user,
    hash_password,
    create_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
)
from ..auth.middleware import get_current_user, is_admin
from .schemas import UserCreate, UserLogin
from .repository import user_exists_by_email, create_user, find_user_by_email, find_tasks_by_user

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


async def create_new_user(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    user_data: UserCreate,
    _: Annotated[None, Depends(RateLimiter(limiter=Limiter(Rate(5, Duration.MINUTE))))],
) -> dict:
    if await user_exists_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cet email est déjà utilisé."
        )
    new_user = await create_user(
        db, user_data.username, user_data.email, hash_password(user_data.password)
    )
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await create_refresh_token(new_user.email, db)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token, httponly=True, samesite="lax", max_age=7 * 24 * 3600
    )
    return {
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at,
    }


async def create_admin_user(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_data: UserCreate,
) -> dict:
    await is_admin(current_user)
    if await user_exists_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cet email est déjà utilisé."
        )
    new_user = await create_user(
        db, user_data.username, user_data.email, hash_password(user_data.password), role="admin"
    )
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await create_refresh_token(new_user.email, db)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token, httponly=True, samesite="lax", max_age=7 * 24 * 3600
    )
    return {
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at,
    }


async def login_for_access_token(
    response: Response,
    form_data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(RateLimiter(limiter=Limiter(Rate(5, Duration.MINUTE))))],
) -> dict:
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh_token = await create_refresh_token(user.email, db)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token, httponly=True, samesite="lax", max_age=7 * 24 * 3600
    )
    return {"token_type": "bearer", "token": access_token}


async def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


async def refresh_access_token(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_session)]
):
    old_refresh = request.cookies.get("refresh_token")
    if not old_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token manquant"
        )
    email = await validate_refresh_token(old_refresh, db)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou expiré"
        )
    user = await find_user_by_email(db, email)
    if not user:
        await revoke_refresh_token(old_refresh, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable"
        )
    await revoke_refresh_token(old_refresh, db)
    new_access_token = create_access_token(
        data={"sub": email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = await create_refresh_token(email, db)
    response.set_cookie(
        "access_token",
        new_access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        "refresh_token", new_refresh_token, httponly=True, samesite="lax", max_age=7 * 24 * 3600
    )
    return {"token_type": "bearer"}


async def logout(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_session)]
):
    refresh = request.cookies.get("refresh_token")
    if refresh:
        await revoke_refresh_token(refresh, db)
    response.delete_cookie("access_token", httponly=True, samesite="lax")
    response.delete_cookie("refresh_token", httponly=True, samesite="lax")
    return {"detail": "Déconnecté avec succès"}


async def get_current_user_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    tasks = await find_tasks_by_user(db, current_user.id)
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
            for task in tasks
        ]
    }
