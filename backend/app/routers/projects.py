from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_project_access, require_project_admin
from app.models import Activity, Project, ProjectMember, ProjectRole, Task, User
from app.schemas import (
    ActivityOut,
    MemberAdd,
    MemberOut,
    MemberUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.services import git_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_out(db: Session, project: Project, user: User) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.member_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    out.task_count = db.query(Task).filter(Task.project_id == project.id).count()
    if user.is_superuser:
        out.my_role = ProjectRole.owner
    else:
        member = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
            .first()
        )
        out.my_role = member.role if member else None
    return out


def _log_activity(db: Session, project: Project, user: User, action: str, target: str, detail: Optional[dict] = None):
    db.add(Activity(project_id=project.id, user_id=user.id, action=action, target=target, detail=detail or {}))


@router.get("", response_model=List[ProjectOut], summary="我参与的项目列表")
def list_projects(
    archived: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Project).filter(Project.is_archived.is_(archived))
    if not user.is_superuser:
        member_ids = (
            db.query(ProjectMember.project_id)
            .filter(ProjectMember.user_id == user.id)
            .subquery()
        )
        query = query.filter(Project.id.in_(member_ids))
    projects = query.order_by(Project.updated_at.desc()).all()
    return [_to_out(db, p, user) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, summary="创建项目(可自动初始化 Git 仓库)")
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.query(Project).filter(Project.key == body.key).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"项目标识 {body.key} 已存在")

    project = Project(
        key=body.key,
        name=body.name,
        description=body.description,
        color=body.color,
        created_by=user.id,
    )
    if body.init_git_repo:
        try:
            project.repo_path = git_service.init_repo(body.key)
        except git_service.GitServiceError as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.owner))
    _log_activity(db, project, user, "create", f"创建了项目 {project.name}",
                  {"repo": bool(project.repo_path)})
    db.commit()
    db.refresh(project)
    return _to_out(db, project, user)


@router.get("/{project_id}", response_model=ProjectOut, summary="项目详情")
def get_project(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = access
    return _to_out(db, project, user)


@router.put("/{project_id}", response_model=ProjectOut, summary="更新项目")
def update_project(
    body: ProjectUpdate,
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = access
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    _log_activity(db, project, user, "update", f"更新了项目设置")
    db.commit()
    db.refresh(project)
    return _to_out(db, project, user)


@router.post("/{project_id}/init-repo", response_model=ProjectOut, summary="为项目初始化 Git 仓库(未初始化时)")
def init_repo(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = access
    if project.repo_path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "项目已有 Git 仓库")
    try:
        project.repo_path = git_service.init_repo(project.key)
    except git_service.GitServiceError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    _log_activity(db, project, user, "init_repo", f"初始化了 Git 仓库 {project.key}.git")
    db.commit()
    db.refresh(project)
    return _to_out(db, project, user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除项目(连同任务与仓库)")
def delete_project(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
):
    project, role = access
    if role != ProjectRole.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅项目所有者可删除项目")
    key = project.key
    db.delete(project)
    db.commit()
    git_service.delete_repo(key)


@router.get("/{project_id}/members", response_model=List[MemberOut], summary="项目成员列表")
def list_members(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_access),
    db: Session = Depends(get_db),
):
    project, _ = access
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.id)
        .all()
    )


@router.post("/{project_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED,
             summary="添加项目成员")
def add_member(
    body: MemberAdd,
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _ = access
    target = db.get(User, body.user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    exists = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == body.user_id)
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "用户已是项目成员")
    if body.role == ProjectRole.owner:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能添加为所有者, 请先转移所有权")
    member = ProjectMember(project_id=project.id, user_id=body.user_id, role=body.role)
    db.add(member)
    _log_activity(db, project, user, "join", f"将 {target.display_name} 添加为成员")
    db.commit()
    db.refresh(member)
    return member


@router.put("/{project_id}/members/{member_id}", response_model=MemberOut, summary="修改成员角色")
def update_member(
    member_id: int,
    body: MemberUpdate,
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
):
    project, _ = access
    member = db.get(ProjectMember, member_id)
    if not member or member.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "成员不存在")
    if member.role == ProjectRole.owner and body.role != ProjectRole.owner:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "项目必须保留一名所有者")
    member.role = body.role
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, summary="移除成员")
def remove_member(
    member_id: int,
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_admin),
    db: Session = Depends(get_db),
):
    project, _ = access
    member = db.get(ProjectMember, member_id)
    if not member or member.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "成员不存在")
    if member.role == ProjectRole.owner:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能移除项目所有者")
    db.delete(member)
    db.commit()


@router.get("/{project_id}/activities", response_model=List[ActivityOut], summary="项目动态")
def project_activities(
    access: "tuple[Project, Optional[ProjectRole]]" = Depends(require_project_access),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    project, _ = access
    return (
        db.query(Activity)
        .filter(Activity.project_id == project.id)
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .all()
    )
