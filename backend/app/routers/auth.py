"""
GateFlow AI — Auth Router
---------------------------
Endpoints:
    POST /api/auth/login    — username + password → JWT access token
    GET  /api/auth/me       — returns current user from bearer token
    POST /api/auth/register — create a new user (hashes password before storing)
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_username,
    hash_password,
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


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str
    role: str = "viewer"


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
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found or inactive."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


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
    user = authenticate_user(db, form.username, form.password)
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
    from app.config import settings
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


# ── POST /api/auth/register ───────────────────────────────────────────────────
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Passwords are bcrypt-hashed before being stored in MySQL.
    """
    if get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "USERNAME_TAKEN",
                    "message": f"Username '{body.username}' is already registered.",
                }
            },
        )
    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New user registered: '{user.username}' (role={user.role})")
    return user
