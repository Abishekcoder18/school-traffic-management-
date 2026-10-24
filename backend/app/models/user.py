"""
GateFlow AI — User ORM Model
------------------------------
Mirrors the `users` table in the `schooltraffic` MySQL database.

If your dump uses different column names, update the Column definitions below
to match exactly — names are case-sensitive in MySQL on Linux hosts.

Expected table DDL (auto-created if not present):
    CREATE TABLE users (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        username    VARCHAR(100) UNIQUE NOT NULL,
        email       VARCHAR(255) UNIQUE NOT NULL,
        full_name   VARCHAR(255),
        role        VARCHAR(50)  DEFAULT 'viewer',
        hashed_password VARCHAR(255) NOT NULL,
        is_active   TINYINT(1)   DEFAULT 1,
        created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP
    );
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username: str = Column(String(100), unique=True, nullable=False, index=True)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    full_name: str = Column(String(255), nullable=True)
    role: str = Column(String(50), default="viewer", nullable=False)
    hashed_password: str = Column(String(255), nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
