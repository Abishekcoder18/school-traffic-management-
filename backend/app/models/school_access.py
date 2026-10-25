from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db import Base


class ManagedSchool(Base):
    __tablename__ = "managed_schools"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(80), unique=True, nullable=False)
    address = Column(String(500), nullable=False, default="")
    city = Column(String(120), nullable=False, default="Chennai")
    contact_phone = Column(String(80), nullable=False, default="")
    active_session = Column(String(120), nullable=False, default="")
    pickup_start = Column(String(20), nullable=False, default="")
    pickup_end = Column(String(20), nullable=False, default="")
    total_gates = Column(Integer, nullable=False, default=0)
    total_vehicles = Column(Integer, nullable=False, default=0)
    pickup_instructions = Column(Text, nullable=False, default="")
    map_place_id = Column(String(255), nullable=True)
    parent_access_enabled = Column(Boolean, nullable=False, default=False)
    traffic_scenario_configured = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class SchoolAdminMembership(Base):
    __tablename__ = "school_admin_memberships"
    __table_args__ = (UniqueConstraint("user_id", "school_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(String(36), ForeignKey("managed_schools.id", ondelete="CASCADE"), nullable=False, index=True)
    can_manage = Column(Boolean, nullable=False, default=True)
    can_create_schools = Column(Boolean, nullable=False, default=False)


class SchoolStudent(Base):
    __tablename__ = "school_students"
    __table_args__ = (UniqueConstraint("id", "school_id"),)

    id = Column(String(36), primary_key=True)
    school_id = Column(String(36), ForeignKey("managed_schools.id", ondelete="CASCADE"), nullable=False, index=True)
    student_name = Column(String(255), nullable=False)
    grade = Column(String(80), nullable=False)
    parent_email = Column(String(255), nullable=False, index=True)
    assigned_gate = Column(String(255), nullable=False)
    arrival_window = Column(String(120), nullable=False)
    pickup_instructions = Column(JSON, nullable=False, default=list)
    notices = Column(JSON, nullable=False, default=list)
    verified_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ParentSchoolMembership(Base):
    __tablename__ = "parent_school_memberships"
    __table_args__ = (UniqueConstraint("user_id", "student_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(String(36), ForeignKey("managed_schools.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    invitation_id = Column(String(36), nullable=False)
    verified_at = Column(DateTime, server_default=func.now(), nullable=False)


class ParentInvitation(Base):
    __tablename__ = "parent_invitations"

    id = Column(String(36), primary_key=True)
    school_id = Column(String(36), ForeignKey("managed_schools.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
