from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.map_annotations import MapAnnotations
from app.models.school_access import (
    ManagedSchool,
    ParentInvitation,
    ParentSchoolMembership,
    SchoolAdminMembership,
    SchoolStudent,
)
from app.models.user import User
from app.routers.auth import get_current_user, require_admin
from app.services.auth_service import hash_password, get_user_by_email
from app.services.data_service import get_scenario
from app.services.map_state_service import MapStateStore

router = APIRouter(prefix="/api/schools", tags=["schools"])


class SchoolOut(BaseModel):
    id: str
    name: str
    code: str
    address: str
    city: str
    contactPhone: str
    activeSession: str
    pickupStart: str
    pickupEnd: str
    totalGates: int
    totalVehicles: int
    pickupInstructions: str
    mapPlaceId: str | None
    parentAccessEnabled: bool
    trafficScenarioConfigured: bool
    canManage: bool = True
    canCreateSchools: bool = False


class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    address: str = Field(min_length=3, max_length=500)
    city: str = Field(min_length=2, max_length=120)
    contactPhone: str = Field(default="", max_length=80)
    activeSession: str = Field(default="", max_length=120)
    pickupStart: str = Field(default="", max_length=20)
    pickupEnd: str = Field(default="", max_length=20)
    totalGates: int = Field(default=0, ge=0, le=100)
    totalVehicles: int = Field(default=0, ge=0)
    pickupInstructions: str = Field(default="", max_length=5000)
    mapPlaceId: str | None = Field(default=None, max_length=255)
    parentAccessEnabled: bool = False


class SchoolUpdate(SchoolCreate):
    pass


class StudentCreate(BaseModel):
    studentName: str = Field(min_length=1, max_length=255)
    grade: str = Field(min_length=1, max_length=80)
    parentEmail: EmailStr
    assignedGate: str = Field(min_length=1, max_length=255)
    arrivalWindow: str = Field(min_length=1, max_length=120)
    pickupInstructions: list[str] = Field(default_factory=list, max_length=20)
    notices: list[str] = Field(default_factory=list, max_length=20)


class StudentOut(BaseModel):
    id: str
    studentName: str
    grade: str
    parentEmail: str
    assignedGate: str
    arrivalWindow: str
    pickupInstructions: list[str]
    notices: list[str]
    verified: bool = True


class InviteCreate(BaseModel):
    studentId: str


class InviteOut(BaseModel):
    invitationUrl: str
    expiresAt: datetime
    email: EmailStr
    studentName: str


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=72)
    fullName: str = Field(min_length=1, max_length=255)


class ParentSchoolOut(BaseModel):
    id: str
    name: str
    city: str


class ParentDashboardOut(BaseModel):
    school: ParentSchoolOut
    student: StudentOut
    notices: list[str]


def _out(
    school: ManagedSchool,
    can_create: bool = False,
    can_manage: bool = True,
) -> SchoolOut:
    return SchoolOut(
        id=school.id,
        name=school.name,
        code=school.code,
        address=school.address,
        city=school.city,
        contactPhone=school.contact_phone,
        activeSession=school.active_session,
        pickupStart=school.pickup_start,
        pickupEnd=school.pickup_end,
        totalGates=school.total_gates,
        totalVehicles=school.total_vehicles,
        pickupInstructions=school.pickup_instructions,
        mapPlaceId=school.map_place_id,
        parentAccessEnabled=school.parent_access_enabled,
        trafficScenarioConfigured=school.traffic_scenario_configured,
        canManage=can_manage,
        canCreateSchools=can_create,
    )


def _parent_school(db: Session, user_id: int, school_id: str) -> ManagedSchool:
    school = (
        db.query(ManagedSchool)
        .join(ParentSchoolMembership, ParentSchoolMembership.school_id == ManagedSchool.id)
        .filter(
            ParentSchoolMembership.user_id == user_id,
            ParentSchoolMembership.school_id == school_id,
            ManagedSchool.parent_access_enabled.is_(True),
        )
        .first()
    )
    if not school:
        raise HTTPException(status_code=403, detail="No active parent membership for this school.")
    return school


def require_school_admin(
    path_school_id: Annotated[str, Path(alias="school_id")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    context_school_id: Annotated[str | None, Header(alias="X-School-ID")] = None,
) -> ManagedSchool:
    if not context_school_id or path_school_id != context_school_id:
        raise HTTPException(status_code=403, detail="School context does not match the requested school.")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="School administrator role required.")
    membership = (
        db.query(SchoolAdminMembership)
        .filter(
            SchoolAdminMembership.user_id == user.id,
            SchoolAdminMembership.school_id == path_school_id,
            SchoolAdminMembership.can_manage.is_(True),
        )
        .first()
    )
    school = db.query(ManagedSchool).filter(ManagedSchool.id == path_school_id).first()
    if not membership or not school:
        raise HTTPException(status_code=403, detail="You are not authorized to manage this school.")
    return school


def require_school_member(
    path_school_id: Annotated[str, Path(alias="school_id")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    context_school_id: Annotated[str | None, Header(alias="X-School-ID")] = None,
) -> ManagedSchool:
    if not context_school_id or path_school_id != context_school_id:
        raise HTTPException(status_code=403, detail="School context does not match the requested school.")
    if user.role == "admin":
        membership = (
            db.query(SchoolAdminMembership)
            .filter(
                SchoolAdminMembership.user_id == user.id,
                SchoolAdminMembership.school_id == path_school_id,
                SchoolAdminMembership.can_manage.is_(True),
            )
            .first()
        )
        school = db.query(ManagedSchool).filter(ManagedSchool.id == path_school_id).first()
        if membership and school:
            return school
    elif user.role == "parent":
        return _parent_school(db, user.id, path_school_id)
    raise HTTPException(status_code=403, detail="You do not have access to this school.")


def require_traffic_admin(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    school_id: Annotated[str | None, Header(alias="X-School-ID")] = None,
) -> ManagedSchool:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="School administrator role required.")
    if not school_id:
        raise HTTPException(status_code=403, detail="A school context is required.")
    membership = (
        db.query(SchoolAdminMembership)
        .filter(
            SchoolAdminMembership.user_id == user.id,
            SchoolAdminMembership.school_id == school_id,
            SchoolAdminMembership.can_manage.is_(True),
        )
        .first()
    )
    school = db.query(ManagedSchool).filter(ManagedSchool.id == school_id).first()
    if not membership or not school:
        raise HTTPException(status_code=403, detail="You are not authorized to manage this school.")
    if not school.traffic_scenario_configured:
        raise HTTPException(
            status_code=409,
            detail="Traffic scenario data has not been configured for this school.",
        )
    return school


@router.get("/mine", response_model=list[SchoolOut])
def get_my_schools(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user.role == "admin":
        can_create_schools = (
            db.query(SchoolAdminMembership)
            .filter(
                SchoolAdminMembership.user_id == user.id,
                SchoolAdminMembership.can_create_schools.is_(True),
            )
            .first()
            is not None
        )
        rows = (
            db.query(ManagedSchool)
            .join(SchoolAdminMembership, SchoolAdminMembership.school_id == ManagedSchool.id)
            .filter(
                SchoolAdminMembership.user_id == user.id,
                SchoolAdminMembership.can_manage.is_(True),
            )
            .order_by(ManagedSchool.name)
            .all()
        )
        return [_out(school, can_create_schools) for school in rows]
    if user.role == "parent":
        rows = (
            db.query(ManagedSchool)
            .join(ParentSchoolMembership, ParentSchoolMembership.school_id == ManagedSchool.id)
            .filter(
                ParentSchoolMembership.user_id == user.id,
                ManagedSchool.parent_access_enabled.is_(True),
            )
            .distinct()
            .order_by(ManagedSchool.name)
            .all()
        )
        return [_out(school, can_manage=False) for school in rows]
    raise HTTPException(status_code=403, detail="Unsupported account role.")


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    body: SchoolCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    grants = (
        db.query(SchoolAdminMembership)
        .filter(
            SchoolAdminMembership.user_id == user.id,
            SchoolAdminMembership.can_create_schools.is_(True),
        )
        .all()
    )
    if not grants:
        raise HTTPException(status_code=403, detail="This administrator cannot create schools.")
    if db.query(ManagedSchool).filter(ManagedSchool.code == body.code).first():
        raise HTTPException(status_code=409, detail="That school code is already in use.")
    school = ManagedSchool(
        id=str(uuid.uuid4()),
        name=body.name,
        code=body.code,
        address=body.address,
        city=body.city,
        contact_phone=body.contactPhone,
        active_session=body.activeSession,
        pickup_start=body.pickupStart,
        pickup_end=body.pickupEnd,
        total_gates=body.totalGates,
        total_vehicles=body.totalVehicles,
        pickup_instructions=body.pickupInstructions,
        map_place_id=body.mapPlaceId,
        parent_access_enabled=body.parentAccessEnabled,
    )
    membership = SchoolAdminMembership(
        user_id=user.id,
        school_id=school.id,
        can_manage=True,
        can_create_schools=False,
    )
    db.add_all([school, membership])
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(school)
    return _out(school)


@router.get("/{school_id}", response_model=SchoolOut)
def get_school(
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
):
    return _out(school)


@router.put("/{school_id}", response_model=SchoolOut)
def update_school(
    body: SchoolUpdate,
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    if body.code != school.code and db.query(ManagedSchool).filter(ManagedSchool.code == body.code).first():
        raise HTTPException(status_code=409, detail="That school code is already in use.")
    school.name = body.name
    school.code = body.code
    school.address = body.address
    school.city = body.city
    school.contact_phone = body.contactPhone
    school.active_session = body.activeSession
    school.pickup_start = body.pickupStart
    school.pickup_end = body.pickupEnd
    school.total_gates = body.totalGates
    school.total_vehicles = body.totalVehicles
    school.pickup_instructions = body.pickupInstructions
    school.map_place_id = body.mapPlaceId
    school.parent_access_enabled = body.parentAccessEnabled
    db.commit()
    db.refresh(school)
    return _out(school)


@router.get("/{school_id}/students", response_model=list[StudentOut])
def list_students(
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    students = db.query(SchoolStudent).filter(SchoolStudent.school_id == school.id).order_by(SchoolStudent.student_name).all()
    return [
        StudentOut(
            id=row.id,
            studentName=row.student_name,
            grade=row.grade,
            parentEmail=row.parent_email,
            assignedGate=row.assigned_gate,
            arrivalWindow=row.arrival_window,
            pickupInstructions=row.pickup_instructions,
            notices=row.notices,
        )
        for row in students
    ]


@router.post("/{school_id}/students", response_model=StudentOut, status_code=201)
def create_student(
    body: StudentCreate,
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    student = SchoolStudent(
        id=str(uuid.uuid4()),
        school_id=school.id,
        student_name=body.studentName,
        grade=body.grade,
        parent_email=body.parentEmail.lower(),
        assigned_gate=body.assignedGate,
        arrival_window=body.arrivalWindow,
        pickup_instructions=body.pickupInstructions,
        notices=body.notices,
        verified_by_admin_id=user.id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentOut(
        id=student.id,
        studentName=student.student_name,
        grade=student.grade,
        parentEmail=student.parent_email,
        assignedGate=student.assigned_gate,
        arrivalWindow=student.arrival_window,
        pickupInstructions=student.pickup_instructions,
        notices=student.notices,
    )


@router.post("/{school_id}/invitations", response_model=InviteOut, status_code=201)
def create_parent_invitation(
    body: InviteCreate,
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    if not school.parent_access_enabled:
        raise HTTPException(status_code=403, detail="Enable parent access before issuing invitations.")
    student = (
        db.query(SchoolStudent)
        .filter(SchoolStudent.id == body.studentId, SchoolStudent.school_id == school.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Verified student record not found in this school.")
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    invitation = ParentInvitation(
        id=str(uuid.uuid4()),
        school_id=school.id,
        student_id=student.id,
        email=student.parent_email,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=expires,
        created_by_user_id=student.verified_by_admin_id,
    )
    db.add(invitation)
    db.commit()
    return InviteOut(
        invitationUrl=f"/?invite={token}",
        expiresAt=expires,
        email=student.parent_email,
        studentName=student.student_name,
    )


@router.post("/invitations/accept", status_code=201)
def accept_invitation(
    body: InvitationAccept,
    db: Annotated[Session, Depends(get_db)],
):
    invitation = (
        db.query(ParentInvitation)
        .filter(
            ParentInvitation.token_hash == hashlib.sha256(body.token.encode()).hexdigest(),
            ParentInvitation.used_at.is_(None),
            ParentInvitation.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not invitation:
        raise HTTPException(status_code=400, detail="Invitation is invalid, expired, or already used.")
    school = db.query(ManagedSchool).filter(ManagedSchool.id == invitation.school_id).first()
    if not school or not school.parent_access_enabled:
        raise HTTPException(status_code=403, detail="Parent access is disabled for this school.")
    student = (
        db.query(SchoolStudent)
        .filter(SchoolStudent.id == invitation.student_id, SchoolStudent.school_id == school.id)
        .first()
    )
    if not student or student.parent_email.lower() != invitation.email.lower():
        raise HTTPException(status_code=403, detail="Invitation no longer matches a verified student record.")
    user = get_user_by_email(db, invitation.email)
    if user and user.role != "parent":
        raise HTTPException(status_code=409, detail="This email belongs to a non-parent account.")
    if not user:
        user = User(
            username=invitation.email.lower(),
            email=invitation.email.lower(),
            full_name=body.fullName,
            role="parent",
            hashed_password=hash_password(body.password),
            is_active=True,
        )
        db.add(user)
        db.flush()
    exists = (
        db.query(ParentSchoolMembership)
        .filter(
            ParentSchoolMembership.user_id == user.id,
            ParentSchoolMembership.student_id == student.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="This parent already has access to the student record.")
    db.add(
        ParentSchoolMembership(
            user_id=user.id,
            school_id=school.id,
            student_id=student.id,
            invitation_id=invitation.id,
        )
    )
    invitation.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "created", "message": "Parent account linked to the verified student record."}


@router.get("/{school_id}/parent-dashboard", response_model=list[ParentDashboardOut])
def get_parent_dashboard(
    school: Annotated[ManagedSchool, Depends(require_school_member)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Parent access required.")
    memberships = (
        db.query(ParentSchoolMembership, SchoolStudent)
        .join(SchoolStudent, SchoolStudent.id == ParentSchoolMembership.student_id)
        .filter(
            ParentSchoolMembership.user_id == user.id,
            ParentSchoolMembership.school_id == school.id,
        )
        .all()
    )
    return [
        ParentDashboardOut(
            school=ParentSchoolOut(id=school.id, name=school.name, city=school.city),
            student=StudentOut(
                id=student.id,
                studentName=student.student_name,
                grade=student.grade,
                parentEmail=student.parent_email,
                assignedGate=student.assigned_gate,
                arrivalWindow=student.arrival_window,
                pickupInstructions=student.pickup_instructions,
                notices=student.notices,
            ),
            notices=student.notices,
        )
        for _, student in memberships
    ]


@router.get("/{school_id}/map")
def get_school_map(
    school: Annotated[ManagedSchool, Depends(require_school_member)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.config import settings

    store = MapStateStore(settings.map_state_path)
    annotations = (
        store.get_annotations(school.map_place_id, storage_key=school.id)
        if school.map_place_id
        else None
    )
    return {"schoolId": school.id, "placeId": school.map_place_id, "annotations": annotations}


@router.put("/{school_id}/map")
def update_school_map(
    body: MapAnnotations,
    school: Annotated[ManagedSchool, Depends(require_school_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.config import settings

    school.map_place_id = body.placeId
    db.commit()
    store = MapStateStore(settings.map_state_path)
    saved = store.save_annotations(body, storage_key=school.id)
    return {"schoolId": school.id, "placeId": school.map_place_id, "annotations": saved}
