from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, get_task_or_404, require_project_access
from app.models import Activity, Comment, Project, ProjectMember, Task, TaskStatus, User
from app.schemas import CommentCreate, CommentOut, TaskCreate, TaskDetail, TaskOut, TaskUpdate

router = APIRouter(tags=["tasks"])

STATUS_FLOW = {
    TaskStatus.todo: {TaskStatus.in_progress, TaskStatus.done},
    TaskStatus.in_progress: {TaskStatus.todo, TaskStatus.testing, TaskStatus.done},
    TaskStatus.testing: {TaskStatus.in_progress, TaskStatus.done},
    TaskStatus.done: {TaskStatus.todo},
}

STATUS_LABELS = {
    TaskStatus.todo: "待办",
    TaskStatus.in_progress: "进行中",
    TaskStatus.testing: "测试中",
    TaskStatus.done: "已完成",
}


def _ensure_task_access(task: Task, user: User, db: Session):
    if user.is_superuser:
        return
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == user.id)
        .first()
    )
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不是该项目成员")


def _log(db: Session, task: Task, user: User, action: str, target: str, detail: Optional[dict] = None):
    db.add(Activity(project_id=task.project_id, task_id=task.id, user_id=user.id,
                    action=action, target=target, detail=detail or {}))


def _to_out(db: Session, task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.comments_count = db.query(Comment).filter(Comment.task_id == task.id).count()
    return out


@router.get("/projects/{project_id}/tasks", response_model=List[TaskOut], summary="项目任务列表(可按状态/关键词过滤)")
def list_tasks(
    project_id: int,
    status: Optional[TaskStatus] = None,
    assignee_id: Optional[int] = None,
    q: str = "",
    db: Session = Depends(get_db),
    access: "tuple[Project, Optional[object]]" = Depends(require_project_access),
):
    query = db.query(Task).filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if q:
        query = query.filter(Task.title.like(f"%{q}%") | Task.number == _safe_int(q))
    return [_to_out(db, t) for t in query.order_by(Task.task_order, Task.id).all()]


def _safe_int(value: str):
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else -1


@router.post("/projects/{project_id}/tasks", response_model=TaskDetail, status_code=status.HTTP_201_CREATED,
             summary="创建任务")
def create_task(
    project_id: int,
    body: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    access: "tuple[Project, Optional[object]]" = Depends(require_project_access),
):
    project, _ = access
    number = (
        db.query(func.coalesce(func.max(Task.number), 0))
        .filter(Task.project_id == project.id)
        .scalar()
    ) + 1
    task = Task(
        project_id=project.id,
        number=number,
        created_by=user.id,
        task_order=number,
        **body.model_dump(),
    )
    db.add(task)
    db.flush()
    _log(db, task, user, "create", f"创建了任务 {project.key}-{number} {task.title}")
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskDetail, summary="任务详情(含评论)")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, task_id)
    _ensure_task_access(task, user, db)
    return task


@router.put("/tasks/{task_id}", response_model=TaskDetail, summary="更新任务(状态流转有校验)")
def update_task(
    task_id: int,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, task_id)
    _ensure_task_access(task, user, db)
    changes = body.model_dump(exclude_unset=True)

    new_status = changes.pop("status", None)
    if new_status is not None and new_status != task.status:
        allowed = STATUS_FLOW.get(task.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"不允许从「{STATUS_LABELS[task.status]}」流转到「{STATUS_LABELS[new_status]}」",
            )
        _log(db, task, user, "status", f"将状态从「{STATUS_LABELS[task.status]}」改为「{STATUS_LABELS[new_status]}」")
        task.status = new_status

    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        new_id = changes["assignee_id"]
        if new_id:
            assignee = db.get(User, new_id)
            if not assignee:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "负责人不存在")
            _log(db, task, user, "assign", f"将任务指派给 {assignee.display_name}")
        else:
            _log(db, task, user, "assign", "取消了任务负责人")

    simple_fields = ("title", "description", "type", "priority", "due_date", "task_order")
    for field in simple_fields:
        if field in changes:
            setattr(task, field, changes[field])

    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除任务")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, task_id)
    _ensure_task_access(task, user, db)
    project = db.get(Project, task.project_id)
    _log(db, task, user, "delete", f"删除了任务 {task.task_key} {task.title}")
    db.delete(task)
    db.commit()


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED,
             summary="发表评论")
def add_comment(
    task_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, task_id)
    _ensure_task_access(task, user, db)
    comment = Comment(task_id=task.id, user_id=user.id, content=body.content)
    db.add(comment)
    _log(db, task, user, "comment", f"评论了任务 {task.task_key}")
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/my/tasks", response_model=List[TaskOut], summary="我的任务(所有项目)")
def my_tasks(
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(Task.assignee_id == user.id)
    if status:
        query = query.filter(Task.status == status)
    else:
        query = query.filter(Task.status != TaskStatus.done)
    return [_to_out(db, t) for t in query.order_by(Task.updated_at.desc()).limit(200).all()]


@router.get("/my/overview", summary="个人工作台统计")
def my_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = db.query(Task).filter(Task.assignee_id == user.id)
    counts = dict(
        base.with_entities(Task.status, func.count(Task.id)).group_by(Task.status).all()
    )
    return {s.value: counts.get(s, 0) for s in TaskStatus}
