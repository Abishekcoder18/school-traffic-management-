"""
GateFlow AI — Auth Router
---------------------------
Endpoints:
    POST /api/auth/login    — username + password → JWT access token
    GET  /api/auth/me       — returns current user from bearer token
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.user import User
from app.models.school_access import ManagedSchool, ParentSchoolMembership
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_username,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Pydantic schemas (request / response) ────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Dependency — get current user from bearer token ──────────────────────────
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token payload missing subject."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user = get_user_by_username(db, username)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "DATABASE_UNAVAILABLE", "message": "Authentication database is unavailable."}},
        ) from exc
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found or inactive."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role not in {"admin", "parent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ROLE_NOT_ALLOWED", "message": "This account has no application role."}},
        )
    return user


def require_roles(*roles: str):
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Your role cannot access this resource."}},
            )
        return current_user

    return dependency


require_authenticated = require_roles("admin", "parent")
require_admin = require_roles("admin")


# ── POST /api/auth/login ──────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """
    Authenticate with username (or email) + password.
    Returns a JWT bearer token valid for 8 hours.
    """
    try:
        user = authenticate_user(db, form.username, form.password)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "DATABASE_UNAVAILABLE", "message": "Authentication database is unavailable."}},
        ) from exc
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Incorrect username or password.",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role not in {"admin", "parent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ROLE_NOT_ALLOWED", "message": "This account has no application role."}},
        )
    if user.role == "parent":
        active_membership = (
            db.query(ParentSchoolMembership)
            .join(ManagedSchool, ManagedSchool.id == ParentSchoolMembership.school_id)
            .filter(
                ParentSchoolMembership.user_id == user.id,
                ManagedSchool.parent_access_enabled.is_(True),
            )
            .first()
        )
        if not active_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Parent access is not enabled for any school linked to this account.",
            )
    token = create_access_token({"sub": user.username, "role": user.role})
    logger.info(f"User '{user.username}' logged in (role={user.role})")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    """Return the currently authenticated user's profile."""
    return current_user
