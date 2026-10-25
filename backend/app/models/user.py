"""
GateFlow AI user records stored in PostgreSQL.
The schema is created from this model by SQLAlchemy at backend startup.
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
