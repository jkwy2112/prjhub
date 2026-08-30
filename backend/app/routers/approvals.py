from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user, get_current_user
from app.models import ApprovalTask, ApprovalTicket, ProcessDefinition, User
from app.schemas_approval import (
    ActionIn,
    ApprovalTaskOut,
    DefinitionDeploy,
    DefinitionOut,
    MyPendingOut,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TreeDeploy,
)
from app.services import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/definitions", response_model=List[DefinitionOut], summary="流程定义(激活版本)")
def list_definitions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = []
    for d in (
        db.query(ProcessDefinition)
        .filter(ProcessDefinition.is_active.is_(True))
        .order_by(ProcessDefinition.id)
        .all()
    ):
        item = DefinitionOut.model_validate(d)
        item.has_tree = bool(d.tree)
        item.logo = d.logo if isinstance(d.logo, dict) else {"icon": "Document", "background": "#409EFF"}
        item.has_form = bool(d.form_items)
        out.append(item)
    return out


@router.post("/definitions", response_model=DefinitionOut, status_code=201, summary="部署 BPMN(超管)")
def deploy_definition(body: DefinitionDeploy, db: Session = Depends(get_db),
                      user: User = Depends(get_admin_user)):
    return approval_service.deploy(db, body.key, body.name, body.bpmn_xml)


@router.post("/definitions/tree", response_model=DefinitionOut, status_code=201,
             summary="保存可视化设计的流程(超管, 表单+流程树一起编译部署)")
def deploy_tree(body: TreeDeploy, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    from app.services.flow_compiler import FlowCompileError

    try:
        return approval_service.deploy_tree(db, body.key, body.name, body.tree,
                                            form_items=body.form_items,
                                            group_name=body.group_name,
                                            remark=body.remark, logo=body.logo)
    except FlowCompileError as exc:
        raise HTTPException(400, str(exc))


@router.get("/definitions/{definition_id}/tree", summary="读取流程树+表单(设计器回显/发起表单解析)")
def get_tree(definition_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    definition = db.get(ProcessDefinition, definition_id)
    if not definition:
        raise HTTPException(404, "流程定义不存在")
    return {"id": definition.id, "key": definition.key, "name": definition.name,
            "version": definition.version, "tree": definition.tree,
            "form_items": definition.form_items or []}


@router.post("", response_model=TicketDetail, status_code=201, summary="发起审批")
def create_ticket(body: TicketCreate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    ticket = approval_service.create_ticket(
        db, body.definition_key, body.title, user.id, body.variables,
        project_id=body.project_id, task_id=body.task_id)
    return _detail(db, ticket, user)


def _ticket_out(db: Session, ticket: ApprovalTicket) -> TicketOut:
    out = TicketOut.model_validate(ticket)
    definition = db.get(ProcessDefinition, ticket.definition_id)
    if definition:
        out.definition_key = definition.key
        out.definition_name = definition.name
    return out


@router.get("/my-pending", response_model=List[MyPendingOut], summary="我的待审批")
def my_pending(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(ApprovalTask, ApprovalTicket)
        .join(ApprovalTicket, ApprovalTask.ticket_id == ApprovalTicket.id)
        .filter(ApprovalTask.assignee_id == user.id,
                ApprovalTask.status == "pending",
                ApprovalTicket.status == "running")
        .order_by(ApprovalTask.id)
        .all()
    )
    return [
        MyPendingOut(
            task_id=row.id,
            node_name=row.node_name,
            ticket=_ticket_out(db, ticket),
        )
        for row, ticket in rows
    ]


@router.get("/my-submitted", response_model=List[TicketDetail], summary="我发起的审批")
def my_submitted(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tickets = (
        db.query(ApprovalTicket)
        .filter(ApprovalTicket.submitted_by == user.id)
        .order_by(ApprovalTicket.id.desc())
        .limit(100)
        .all()
    )
    return [_detail(db, t, user) for t in tickets]


def _detail(db: Session, ticket: ApprovalTicket, user: User) -> TicketDetail:
    detail = TicketDetail.model_validate(ticket)
    definition = db.get(ProcessDefinition, ticket.definition_id)
    if definition:
        detail.definition_key = definition.key
        detail.definition_name = definition.name
    detail.tasks = [
        ApprovalTaskOut.model_validate(t)
        for t in db.query(ApprovalTask)
        .filter(ApprovalTask.ticket_id == ticket.id)
        .order_by(ApprovalTask.id)
        .all()
    ]
    pending = next(
        (t.id for t in detail.tasks if t.status == "pending" and t.assignee_id == user.id),
        None,
    )
    detail.my_pending_task_id = pending
    definition = db.get(ProcessDefinition, ticket.definition_id)
    if definition and definition.form_items:
        detail.form_items = definition.form_items
        detail.form_values = {
            k: v for k, v in (ticket.variables or {}).items()
            if any(f.get("id") == k for f in definition.form_items)
        }
        # form permissions of MY pending approval node (for perm-filtered display)
        if pending is not None:
            my_task = next((t for t in detail.tasks if t.id == pending), None)
            node_meta = (definition.node_meta or {}).get(my_task.node_id) if my_task else None
            if node_meta and node_meta.get("type") == "APPROVAL":
                detail.my_node_form_perms = node_meta.get("formPerms") or {}
    return detail


@router.get("/{ticket_id}", response_model=TicketDetail, summary="审批单详情(时间线)")
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.get(ApprovalTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "审批单不存在")
    return _detail(db, ticket, user)


@router.post("/tasks/{approval_task_id}/complete", response_model=TicketDetail,
             summary="审批(同意/驳回)")
def complete_approval_task(approval_task_id: int, body: ActionIn,
                           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(ApprovalTask, approval_task_id)
    if not row:
        raise HTTPException(404, "审批任务不存在")
    ticket = approval_service.complete_task(db, row, user, body.action, body.comment)
    return _detail(db, ticket, user)


@router.post("/{ticket_id}/cancel", response_model=TicketDetail, summary="撤回审批(发起人)")
def cancel_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.get(ApprovalTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "审批单不存在")
    approval_service.cancel_ticket(db, ticket, user)
    return _detail(db, ticket, user)
