from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    print(f"DEBUG: Payload reçu: {payload}")
    if payload is None or payload.get("type") != "access":
        print("DEBUG: Echec sur le check du type ou payload None")
        raise credentials_exception

    user_id: str = payload.get("sub")
    print(f"DEBUG: User ID extrait: '{user_id}'")
    if user_id is None:
        raise credentials_exception

    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Utilisateur inactif")
    return current_user

async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilèges insuffisants. Accès administrateur requis"
        )
    return current_user