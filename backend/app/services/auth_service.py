"""
GateFlow AI — Authentication Service
--------------------------------------
Handles:
  - Password hashing / verification  (bcrypt via passlib)
  - JWT creation / decoding          (python-jose)
  - User lookup from PostgreSQL       (SQLAlchemy session)
  - create_tables() — idempotent DDL  (run once on startup)
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import NAMESPACE_URL, uuid5

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import Base, engine
from app.models.school_access import ManagedSchool, SchoolAdminMembership
from app.models.user import User
from app.services.data_service import get_scenario

logger = logging.getLogger(__name__)

def hash_password(plain: str) -> str:
    password = plain.encode("utf-8")
    if len(password) > 72:
        raise ValueError("Passwords must be no longer than 72 UTF-8 bytes.")
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    password = plain.encode("utf-8")
    if len(password) > 72:
        return False
    return bcrypt.checkpw(password, hashed.encode("ascii"))


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
def create_tables() -> bool:
    """
    Create all ORM-managed tables if they do not already exist.
    Safe to call on every startup — existing tables are NOT dropped.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ PostgreSQL tables verified / created.")
        return True
    except Exception as exc:
        logger.error(f"❌ Failed to create PostgreSQL tables: {exc}")
        return False


def seed_demo_users() -> None:
    """Create the initial school administrator account if it is missing."""
    SessionFactory = sessionmaker(bind=engine)
    credentials_path = Path(__file__).resolve().parents[2] / ".seed-users.json"
    existing_credentials = []
    if credentials_path.exists():
        try:
            existing_credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("The local seed-credentials file is unreadable.") from exc

    accounts = [
        {
            "username": "admin@oakridge.edu",
            "email": "admin@oakridge.edu",
            "full_name": "Oakridge School Administrator",
            "role": "admin",
        },
    ]
    if not isinstance(existing_credentials, list):
        raise RuntimeError("The local seed-credentials file must contain a JSON list.")
    credentials = existing_credentials
    saved_by_email = {
        entry.get("email"): entry
        for entry in credentials
        if isinstance(entry, dict) and entry.get("email")
    }

    with SessionFactory() as db:
        created = False
        for account in accounts:
            if get_user_by_email(db, account["email"]):
                continue
            saved = saved_by_email.get(account["email"], {})
            password = saved.get("password") or secrets.token_urlsafe(24)
            user = User(
                **account,
                hashed_password=hash_password(password),
                is_active=True,
            )
            db.add(user)
            if not saved:
                credentials.append({**account, "password": password})
                saved_by_email[account["email"]] = credentials[-1]
            created = True
        if created:
            temporary = credentials_path.with_suffix(".tmp")
            try:
                temporary.write_text(
                    json.dumps(credentials, indent=2),
                    encoding="utf-8",
                )
                temporary.replace(credentials_path)
                db.commit()
            except OSError:
                db.rollback()
                temporary.unlink(missing_ok=True)
                raise
            logger.warning(
                "Created missing demo accounts. One-time credentials are in "
                "backend/.seed-users.json; remove that file after securely recording them."
            )


def seed_default_school() -> None:
    """Attach the existing synthetic Oakridge scenario to its seeded admin."""
    SessionFactory = sessionmaker(bind=engine)
    scenario = get_scenario()
    school_data = scenario.school
    school_code = school_data.code
    school_id = str(uuid5(NAMESPACE_URL, f"gateflow:school:{school_code}"))
    with SessionFactory() as db:
        user = get_user_by_email(db, "admin@oakridge.edu")
        if not user or user.role != "admin":
            raise RuntimeError("Seed administrator is missing or has an invalid role.")
        school = db.query(ManagedSchool).filter(ManagedSchool.code == school_code).first()
        if not school:
            school = ManagedSchool(
                id=school_id,
                name=school_data.name,
                code=school_code,
                address="",
                city="Chennai",
                contact_phone=school_data.schoolContactPhone,
                active_session=school_data.activeSession,
                pickup_start=school_data.timeWindowStart,
                pickup_end=school_data.timeWindowEnd,
                total_gates=school_data.totalGates,
                total_vehicles=school_data.totalVehicles,
                pickup_instructions="",
                parent_access_enabled=False,
                traffic_scenario_configured=True,
            )
            db.add(school)
            db.flush()
        school.traffic_scenario_configured = True
        membership = (
            db.query(SchoolAdminMembership)
            .filter(
                SchoolAdminMembership.user_id == user.id,
                SchoolAdminMembership.school_id == school.id,
            )
            .first()
        )
        if not membership:
            db.add(
                SchoolAdminMembership(
                    user_id=user.id,
                    school_id=school.id,
                    can_manage=True,
                    can_create_schools=True,
                )
            )
        db.commit()
