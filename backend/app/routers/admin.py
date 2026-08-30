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
    dept: Optional[str] = Field(default=None, max_length=128)
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


# ---------- auth configuration (LDAP / WeCom) ----------


class LDAPConfigIn(BaseModel):
    enabled: Optional[bool] = None
    server: Optional[str] = None
    use_ssl: Optional[bool] = None
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    search_base: Optional[str] = None
    search_filter: Optional[str] = None
    attr_username: Optional[str] = None
    attr_display_name: Optional[str] = None
    attr_email: Optional[str] = None


class WeComConfigIn(BaseModel):
    enabled: Optional[bool] = None
    corp_id: Optional[str] = None
    corp_secret: Optional[str] = None
    agent_id: Optional[str] = None


def _resolved_config(db: Session, section: str) -> dict:
    from app.services import config_service

    if section == "ldap":
        cfg = config_service.ldap_config(db)
        secret_field = "bind_password"
    else:
        cfg = config_service.wecom_config(db)
        secret_field = "corp_secret"
    out = dict(cfg)
    if out.get(secret_field):
        out[secret_field] = "******"
    return out


@router.get("/auth-config", summary="读取认证配置(密码脱敏)")
def get_auth_config(db: Session = Depends(get_db)):
    return {"ldap": _resolved_config(db, "ldap"), "wecom": _resolved_config(db, "wecom")}


@router.put("/auth-config/ldap", summary="保存 LDAP 配置")
def save_ldap_config(body: LDAPConfigIn, db: Session = Depends(get_db)):
    from app.services import config_service

    config_service.save_ldap_config(db, body.model_dump(exclude_unset=True))
    return {"ok": True}


@router.put("/auth-config/wecom", summary="保存企业微信配置")
def save_wecom_config(body: WeComConfigIn, db: Session = Depends(get_db)):
    from app.services import config_service

    config_service.save_wecom_config(db, body.model_dump(exclude_unset=True))
    return {"ok": True}


def _merge_for_test(saved: dict, incoming: dict, secret_field: str) -> dict:
    cfg = dict(saved)
    incoming = dict(incoming)
    if incoming.get(secret_field) == "******" or incoming.get(secret_field) is None:
        incoming.pop(secret_field, None)
    cfg.update({k: v for k, v in incoming.items() if v is not None})
    return cfg


@router.post("/auth-config/ldap/test", summary="测试 LDAP 连接(按表单当前值, 未保存也可测)")
def test_ldap(body: LDAPConfigIn, db: Session = Depends(get_db)):
    from app.services import config_service, ldap_service

    saved = config_service.ldap_config(db)
    cfg = _merge_for_test(saved, body.model_dump(exclude_unset=True), "bind_password")
    if not cfg.get("enabled"):
        cfg["enabled"] = True  # allow testing even if not enabled yet
    ok, message = ldap_service.test_connection(cfg)
    return {"ok": ok, "message": message}


@router.post("/auth-config/wecom/test", summary="测试企业微信连接(按表单当前值)")
def test_wecom(body: WeComConfigIn, db: Session = Depends(get_db)):
    from app.services import config_service, wecom_service

    saved = config_service.wecom_config(db)
    cfg = _merge_for_test(saved, body.model_dump(exclude_unset=True), "corp_secret")
    ok, message = wecom_service.test_connection(cfg)
    return {"ok": ok, "message": message}
