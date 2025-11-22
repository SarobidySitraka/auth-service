from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Créer un nouveau compte utilisateur"""

    email = cast(str, user_in.email)
    existing_user = await UserService.get_by_email(db, email=email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )

    existing_username = await UserService.get_by_username(db, user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris"
        )

    user = await UserService.create(db, user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """Connexion et obtention de tokens"""
    user = await UserService.authenticate(db, form_data.username, form_data.password)
    is_active = None
    if user:
        is_active = user.is_active
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur inactif"
        )

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
        refresh_token_var: str,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """Rafraîchir le token d'accès"""
    payload = decode_token(refresh_token_var)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de rafraîchissement invalide"
        )

    user_id = payload.get("sub")
    user = await UserService.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé ou inactif"
        )

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Obtenir les informations de l'utilisateur connecté"""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """Modifier les informations de l'utilisateur connecté"""
    if user_update.email and user_update.email != current_user.email:
        email = cast(str, user_update.email)
        existing = await UserService.get_by_email(db, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )

    if user_update.username and user_update.username != current_user.username:
        existing = await UserService.get_by_username(db, user_update.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà pris"
            )

    user = await UserService.update(db, current_user, user_update)
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """Supprimer le compte de l'utilisateur connecté"""
    await UserService.delete(db, current_user)