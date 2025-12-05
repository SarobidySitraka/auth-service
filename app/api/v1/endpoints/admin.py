from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_superuser
from app.models.user import User
from app.schemas.user import AdminUserCreate, AdminUserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_admin: Annotated[User, Depends(get_current_superuser)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None
):
    """
    Récupérer tous les utilisateurs (admin seulement)
    
    - **skip**: Nombre d'utilisateurs à ignorer (pagination)
    - **limit**: Nombre maximum d'utilisateurs à retourner
    """
    users = await UserService.get_all(db, skip=skip, limit=limit)
    return users


@router.get("/users/count")
async def count_users(
    current_admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Compter le nombre total d'utilisateurs (admin seulement)"""
    count = await UserService.count_all(db)
    return {"total": count}


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Récupérer un utilisateur par ID (admin seulement)"""
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: AdminUserCreate,
    current_admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Créer un nouvel utilisateur (admin seulement)
    
    Permet de créer un utilisateur avec des privilèges spécifiques
    """
    # Vérifier si l'email existe déjà
    existing_user = await UserService.get_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Vérifier si le username existe déjà
    existing_username = await UserService.get_by_username(db, user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris"
        )
    
    user = await UserService.create_admin(db, user_in)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: AdminUserUpdate,
    current_admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Mettre à jour un utilisateur (admin seulement)
    
    Permet de modifier tous les attributs d'un utilisateur, y compris les privilèges
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier l'unicité de l'email si modifié
    if user_update.email and user_update.email != user.email:
        existing = await UserService.get_by_email(db, user_update.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
    
    # Vérifier l'unicité du username si modifié
    if user_update.username and user_update.username != user.username:
        existing = await UserService.get_by_username(db, user_update.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà pris"
            )
    
    # Empêcher un admin de se retirer ses propres privilèges
    if user_id == current_admin.id and user_update.is_superuser is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas retirer vos propres privilèges d'administrateur"
        )
    
    updated_user = await UserService.update_admin(db, user, user_update)
    return updated_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Supprimer un utilisateur (admin seulement)
    
    Note: Un administrateur ne peut pas se supprimer lui-même
    """
    # Empêcher un admin de se supprimer lui-même
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    await UserService.delete(db, user)