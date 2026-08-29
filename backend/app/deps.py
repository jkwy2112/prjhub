from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models import Project, ProjectMember, ProjectRole, Task, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未认证")
    username = decode_access_token(credentials.credentials)
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌无效或已过期")
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已禁用")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "项目不存在")
    return project


def require_project_access(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> "tuple[Project, Optional[ProjectRole]]":
    project = get_project_or_404(db, project_id)
    role = None
    if user.is_superuser:
        role = ProjectRole.owner
    else:
        member = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
            .first()
        )
        if member:
            role = member.role
    if role is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不是该项目成员")
    return project, role


def require_project_admin(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_access),
) -> "tuple[Project, Optional[ProjectRole]]":
    project, role = access
    if role not in (ProjectRole.owner, ProjectRole.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要项目管理员权限")
    return access


def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
    return task
