"""
GateFlow AI — Authentication Service
--------------------------------------
Handles:
  - Password hashing / verification  (bcrypt via passlib)
  - JWT creation / decoding          (python-jose)
  - User lookup from MySQL            (SQLAlchemy session)
  - create_tables() — idempotent DDL  (run once on startup)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ── User queries ──────────────────────────────────────────────────────────────
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Looks up user by username (or email) and verifies bcrypt password.
    Returns the User object on success, None on failure.
    """
    # Try username first, then email
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
    if not user:
        logger.warning(f"Login attempt for unknown user: '{username}'")
        return None
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: '{username}'")
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Wrong password for user: '{username}'")
        return None
    return user


# ── Table creation (idempotent) ───────────────────────────────────────────────
def create_tables() -> None:
    """
    Create all ORM-managed tables if they do not already exist.
    Safe to call on every startup — existing tables are NOT dropped.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ MySQL tables verified / created.")
    except Exception as exc:
        logger.error(f"❌ Failed to create MySQL tables: {exc}")
