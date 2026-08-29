"""System admin panel APIs (superuser only): stats, user management."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import get_db
from app.deps import get_admin_user
from app.models import AuthType, Project, ProjectMember, Task, TaskStatus, User
from app.core.config import settings
from app.schemas import UserOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


class AdminUserOut(UserOut):
    project_count: int = 0


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    name: str = Field(default="", max_length=128)
    email: str = Field(default="", max_length=255)
    password: str = Field(min_length=6, max_length=128)
    is_superuser: bool = False


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    email: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class AdminStatsOut(BaseModel):
    user_count: int
    active_user_count: int
    project_count: int
    archived_project_count: int
    task_count: int
    task_status_distribution: dict
    repo_count: int
    auth_options: dict
    recent_users: List[UserOut]


@router.get("/stats", response_model=AdminStatsOut, summary="系统概览统计")
def stats(db: Session = Depends(get_db)):
    status_rows = dict(db.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
    recent = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    return AdminStatsOut(
        user_count=db.query(User).count(),
        active_user_count=db.query(User).filter(User.is_active.is_(True)).count(),
        project_count=db.query(Project).filter(Project.is_archived.is_(False)).count(),
        archived_project_count=db.query(Project).filter(Project.is_archived.is_(True)).count(),
        task_count=db.query(Task).count(),
        task_status_distribution={s.value: status_rows.get(s, 0) for s in TaskStatus},
        repo_count=db.query(Project).filter(Project.repo_path != "").count(),
        auth_options={"ldap_enabled": settings.LDAP_ENABLED, "wecom_enabled": settings.WECOM_ENABLED},
        recent_users=recent,
    )


@router.get("/users", response_model=List[AdminUserOut], summary="全部用户列表")
def list_users(
    q: str = "",
    auth_type: Optional[AuthType] = None,
    db: Session = Depends(get_db),
    limit: int = Query(200, le=500),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter(User.username.like(like) | User.name.like(like) | User.email.like(like))
    if auth_type:
        query = query.filter(User.auth_type == auth_type)
    users = query.order_by(User.id).limit(limit).all()

    counts: dict = dict(
        db.query(ProjectMember.user_id, func.count(ProjectMember.id)).group_by(ProjectMember.user_id).all()
    )
    result = []
    for u in users:
        out = AdminUserOut.model_validate(u)
        out.project_count = counts.get(u.id, 0)
        result.append(out)
    return result


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED, summary="创建本地用户")
def create_user(body: AdminUserCreate, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"用户名 {username} 已存在")
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        name=body.name or username,
        email=body.email,
        auth_type=AuthType.local,
        is_active=True,
        is_superuser=body.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_user_or_404(db: Session, user_id: int, admin: User) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能对当前登录账号执行此操作")
    return user


@router.put("/users/{user_id}", response_model=AdminUserOut, summary="更新用户(禁用/授权/改密)")
def update_user(user_id: int, body: AdminUserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(get_admin_user)):
    user = _get_user_or_404(db, user_id, admin)
    changes = body.model_dump(exclude_unset=True)

    if (changes.get("is_superuser") is False and user.is_superuser
            and db.query(User).filter(User.is_superuser.is_(True)).count() <= 1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "系统必须保留至少一名超级管理员")

    new_password = changes.pop("password", None)
    if new_password:
        user.password_hash = hash_password(new_password)
    if changes.get("is_active") is False:
        changes["password_hash"] = ""  # disable drops credentials
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
