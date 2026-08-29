"""Workflow definition APIs: list/read for everyone, write for admins."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user, get_current_user
from app.models import User
from app.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["workflow"])


class NodeIn(BaseModel):
    key: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=32)
    color: str = "#409EFF"
    x: float = 0
    y: float = 0
    is_initial: bool = False
    is_done: bool = False
    next_keys: List[str] = []
    handler_type: str = "any"
    handler_user_ids: List[int] = []


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=255)
    is_default: bool = False
    nodes: List[NodeIn] = []


class WorkflowSave(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=255)
    nodes: List[NodeIn] = []


@router.get("", summary="工作流列表")
def list_workflows(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workflow_service.list_workflows(db)


@router.get("/default", summary="默认工作流(看板/统计渲染用)")
def get_default(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workflow_service.workflow_payload(workflow_service.default_workflow(db))


@router.get("/{workflow_id}", summary="工作流详情")
def get_workflow(workflow_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workflow_service.workflow_payload(workflow_service.get_or_404(db, workflow_id))


@router.post("", status_code=201, summary="创建工作流(超管)")
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    wf = workflow_service.create_workflow(
        db, name=body.name, description=body.description,
        nodes=[n.model_dump() for n in body.nodes] or None, is_default=body.is_default)
    return workflow_service.workflow_payload(wf)


@router.put("/{workflow_id}", summary="保存工作流(超管, 含节点布局/连线/处理人)")
def save_workflow(workflow_id: int, body: WorkflowSave, db: Session = Depends(get_db),
                  user: User = Depends(get_admin_user)):
    wf = workflow_service.get_or_404(db, workflow_id)
    migrated = workflow_service.save_workflow(
        db, wf, body.name, body.description, [n.model_dump() for n in body.nodes])
    return {"ok": True, "migrated": migrated}


@router.post("/{workflow_id}/default", summary="设为默认工作流(超管)")
def set_default(workflow_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    from sqlalchemy import update

    from app.models import Workflow

    wf = workflow_service.get_or_404(db, workflow_id)
    db.execute(update(Workflow).values(is_default=False))
    wf.is_default = True
    db.commit()
    return {"ok": True}


@router.delete("/{workflow_id}", summary="删除工作流(超管, 未被项目绑定)")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    workflow_service.delete_workflow(db, workflow_service.get_or_404(db, workflow_id))
    return {"ok": True}
