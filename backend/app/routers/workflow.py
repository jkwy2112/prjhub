"""Customizable workflow APIs: read for everyone (kanban), write for admins."""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user
from app.models import User
from app.services import workflow_service

router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowStatusIn(BaseModel):
    key: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=32)
    color: str = "#409EFF"
    is_initial: bool = False
    is_done: bool = False
    next_keys: List[str] = []


class WorkflowOut(BaseModel):
    statuses: List[dict]
    used_keys: List[str]


@router.get("", response_model=WorkflowOut, summary="当前工作流(状态+流转规则)")
def get_workflow(db: Session = Depends(get_db)):
    from app.models import Task

    used = [row[0] for row in db.query(Task.status).distinct().all() if row[0]]
    statuses = [
        {"id": s.id, "key": s.key, "name": s.name, "color": s.color, "sort_order": s.sort_order,
         "is_initial": s.is_initial, "is_done": s.is_done, "next_keys": s.next_keys or []}
        for s in workflow_service.get_statuses(db)
    ]
    return {"statuses": statuses, "used_keys": used}


class WorkflowSave(BaseModel):
    statuses: List[WorkflowStatusIn]


@router.put("", summary="整体保存工作流(超管, 删除状态的任务自动迁回初始状态)")
def save_workflow(body: WorkflowSave, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    _, migrated = workflow_service.save_workflow(db, [s.model_dump() for s in body.statuses])
    return {"ok": True, "migrated": migrated}


@router.post("/reset", summary="恢复默认工作流(超管)")
def reset_workflow(db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    workflow_service.reset_to_default(db)
    return {"ok": True}
