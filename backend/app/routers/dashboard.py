from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Activity, ProjectMember, Task, TaskType, User
from app.schemas import ActivityOut, DashboardOut, TaskOut
from app.services import workflow_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut, summary="仪表盘")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member_project_ids = [m[0] for m in db.query(ProjectMember.project_id)
                          .filter(ProjectMember.user_id == user.id).all()]

    project_count = len(member_project_ids)

    base = db.query(Task)
    if member_project_ids:
        base = base.filter(Task.project_id.in_(member_project_ids))
    else:
        base = base.filter(Task.id < 0)  # no projects yet -> empty set

    statuses = workflow_service.default_workflow(db).nodes
    done = [s.key for s in statuses if s.is_done]

    my_open = base.filter(Task.assignee_id == user.id, Task.status.notin_(done)).count()
    overdue = base.filter(
        Task.assignee_id == user.id,
        Task.status.notin_(done),
        Task.due_date.is_not(None),
        Task.due_date < func.now(),
    ).count()
    done_count = base.filter(Task.assignee_id == user.id, Task.status.in_(done)).count()

    status_rows = dict(base.with_entities(Task.status, func.count(Task.id)).group_by(Task.status).all())
    distribution = {s.key: status_rows.get(s.key, 0) for s in statuses}
    distribution["other"] = sum(v for k, v in status_rows.items() if k not in distribution)
    type_rows = dict(base.with_entities(Task.type, func.count(Task.id)).group_by(Task.type).all())

    my_recent = (
        db.query(Task)
        .filter(Task.assignee_id == user.id, Task.status.notin_(done))
        .order_by(Task.updated_at.desc())
        .limit(10)
        .all()
    )

    activities: List[Activity] = []
    if member_project_ids:
        activities = (
            db.query(Activity)
            .filter(Activity.project_id.in_(member_project_ids))
            .order_by(Activity.created_at.desc())
            .limit(15)
            .all()
        )

    return DashboardOut(
        project_count=project_count,
        my_open_task_count=my_open,
        overdue_task_count=overdue,
        done_task_count=done_count,
        status_distribution=distribution,
        type_distribution={t.value: type_rows.get(t, 0) for t in TaskType},
        my_recent_tasks=my_recent,
        recent_activities=activities,
    )
