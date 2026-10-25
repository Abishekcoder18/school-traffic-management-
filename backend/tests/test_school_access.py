from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models.school_access import (
    ManagedSchool,
    ParentSchoolMembership,
    SchoolStudent,
)
from app.models.user import User
from app.routers.auth import get_current_user


@pytest.fixture
def parent_school_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    with factory() as db:
        admin = User(
            username="school-admin-test",
            email="school-admin-test@example.test",
            full_name="School Admin",
            role="admin",
            hashed_password="unused",
            is_active=True,
        )
        parent = User(
            username="parent-test",
            email="parent-test@example.test",
            full_name="Parent",
            role="parent",
            hashed_password="unused",
            is_active=True,
        )
        school = ManagedSchool(
            id="school-a",
            name="School A",
            code="SCHOOL_A",
            address="1 Main Road",
            city="Chennai",
            parent_access_enabled=True,
        )
        other_school = ManagedSchool(
            id="school-b",
            name="School B",
            code="SCHOOL_B",
            address="2 Main Road",
            city="Chennai",
            parent_access_enabled=True,
        )
        db.add_all([admin, parent, school, other_school])
        db.flush()
        student = SchoolStudent(
            id="student-a",
            school_id=school.id,
            student_name="Student A",
            grade="Grade 4",
            parent_email=parent.email,
            assigned_gate="Gate 1",
            arrival_window="15:00",
            pickup_instructions=["Use north entrance"],
            notices=["Early dismissal Friday"],
            verified_by_admin_id=admin.id,
        )
        db.add(student)
        db.flush()
        db.add(
            ParentSchoolMembership(
                user_id=parent.id,
                school_id=school.id,
                student_id=student.id,
                invitation_id="invitation-a",
            )
        )
        db.commit()
        parent_id = parent.id

    def override_db():
        with factory() as db:
            yield db

    old_db_override = app.dependency_overrides.get(get_db)
    old_user_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=parent_id,
        role="parent",
    )
    try:
        yield TestClient(app), factory
    finally:
        if old_db_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = old_db_override
        if old_user_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user_override
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_parent_access_is_limited_to_verified_school_membership(parent_school_client):
    client, _ = parent_school_client

    schools = client.get("/api/schools/mine")
    assert schools.status_code == 200
    assert [school["id"] for school in schools.json()] == ["school-a"]
    assert schools.json()[0]["canManage"] is False

    dashboard = client.get(
        "/api/schools/school-a/parent-dashboard",
        headers={"X-School-ID": "school-a"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()[0]["student"]["studentName"] == "Student A"

    unauthorized = client.get(
        "/api/schools/school-b/map",
        headers={"X-School-ID": "school-b"},
    )
    assert unauthorized.status_code == 403

    mismatched_context = client.get(
        "/api/schools/school-a/parent-dashboard",
        headers={"X-School-ID": "school-b"},
    )
    assert mismatched_context.status_code == 403


def test_disabling_parent_access_blocks_existing_parent_requests(parent_school_client):
    client, factory = parent_school_client
    with factory() as db:
        db.query(ManagedSchool).filter(ManagedSchool.id == "school-a").update(
            {ManagedSchool.parent_access_enabled: False}
        )
        db.commit()

    assert client.get("/api/schools/mine").json() == []
    denied = client.get(
        "/api/schools/school-a/parent-dashboard",
        headers={"X-School-ID": "school-a"},
    )
    assert denied.status_code == 403
