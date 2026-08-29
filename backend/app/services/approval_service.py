"""Approval business service: tickets, pending-task sync, actions. Engine-agnostic."""
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ApprovalTask, ApprovalTicket, ProcessDefinition, Project, Task, User
from app.services import bpmn_engine

logger = logging.getLogger(__name__)

GENERIC_KEY = "generic_approval"

# end event id -> ticket status
END_STATUS = {"end_approved": "approved", "end_rejected": "rejected"}


def deploy(db: Session, key: str, name: str, bpmn_xml: str) -> ProcessDefinition:
    bpmn_engine.parse_spec(bpmn_xml)  # validate before storing
    last = (
        db.query(ProcessDefinition)
        .filter(ProcessDefinition.key == key)
        .order_by(ProcessDefinition.version.desc())
        .first()
    )
    version = (last.version + 1) if last else 1
    if last:
        last.is_active = False
    definition = ProcessDefinition(key=key, name=name or key, version=version,
                                   bpmn_xml=bpmn_xml, is_active=True)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    logger.info("deployed process %s v%s", key, version)
    return definition


def seed_templates(db: Session) -> None:
    if not db.query(ProcessDefinition).filter(ProcessDefinition.key == GENERIC_KEY).first():
        from app.services.bpmn_templates import GENERIC_APPROVAL_BPMN

        deploy(db, GENERIC_KEY, "通用审批流(条件金额分支/会签或签)", GENERIC_APPROVAL_BPMN)


def active_definition(db: Session, key: str) -> ProcessDefinition:
    definition = (
        db.query(ProcessDefinition)
        .filter(ProcessDefinition.key == key, ProcessDefinition.is_active.is_(True))
        .first()
    )
    if not definition:
        raise HTTPException(404, f"流程定义 {key} 不存在")
    return definition


def _resolve_assignees(ticket_vars: dict, node_id: str) -> list:
    """Convention: ut_cs <- variables['countersigners']; others <- variables['approver_<name>'].

    'approver_<name>' matches the node id without the leading task-type prefix, e.g.
    ut_l1 -> approver_l1 (falls back to approver_ut_l1).
    """
    if node_id == "ut_cs":
        return list(ticket_vars.get("countersigners") or [])
    short = node_id[3:] if node_id.startswith("ut_") else node_id
    value = ticket_vars.get(f"approver_{short}", ticket_vars.get(f"approver_{node_id}"))
    return [value] if value else []


def _sync_tasks(db: Session, ticket: ApprovalTicket, wf) -> None:
    """Mirror engine READY user tasks into ApprovalTask rows; cancel rows no longer ready."""
    ready = bpmn_engine.ready_user_tasks(wf)
    ready_ids = {t.engine_task_id for t in ready}

    rows = db.query(ApprovalTask).filter(ApprovalTask.ticket_id == ticket.id).all()
    by_engine_id = {r.engine_task_id: r for r in rows}

    for row in rows:
        if row.status == "pending" and row.engine_task_id not in ready_ids:
            row.status = "cancelled"  # e.g. terminated by or-sign completion / rejection shortcut

    # assignee allocation per node, stable by (node_id, engine_task_id)
    allocated: "dict[str, list[int]]" = {}
    for row in sorted(rows, key=lambda r: r.engine_task_id):
        if row.assignee_id is not None:
            allocated.setdefault(row.node_id, []).append(row.assignee_id)

    for et in sorted(ready, key=lambda t: t.engine_task_id):
        if et.engine_task_id in by_engine_id:
            continue
        candidates = _resolve_assignees(ticket.variables or {}, et.node_id)
        used = allocated.setdefault(et.node_id, [])
        assignee = None
        for cand in candidates:
            if cand not in used:
                assignee = cand
                break
        if assignee is not None:
            used.append(assignee)
        db.add(ApprovalTask(
            ticket_id=ticket.id,
            engine_task_id=et.engine_task_id,
            node_id=et.node_id,
            node_name=et.node_name,
            assignee_id=assignee,
            status="pending",
        ))


def _persist(db: Session, ticket: ApprovalTicket, wf) -> None:
    ticket.engine_state = bpmn_engine.save_state(wf)
    end_id = bpmn_engine.reached_end(wf)
    if end_id is not None:
        ticket.status = END_STATUS.get(end_id, "approved")
        from app.models import utcnow

        ticket.finished_at = utcnow()
        for row in db.query(ApprovalTask).filter(ApprovalTask.ticket_id == ticket.id,
                                                 ApprovalTask.status == "pending"):
            row.status = "cancelled"
    _sync_tasks(db, ticket, wf)
    db.commit()


def create_ticket(db: Session, definition_key: str, title: str, submitted_by: int,
                  variables: dict, project_id: Optional[int] = None,
                  task_id: Optional[int] = None) -> ApprovalTicket:
    definition = active_definition(db, definition_key)
    if project_id and not db.get(Project, project_id):
        raise HTTPException(404, "关联项目不存在")
    if task_id and not db.get(Task, task_id):
        raise HTTPException(404, "关联任务不存在")

    wf = bpmn_engine.start_workflow(definition.bpmn_xml)
    bpmn_engine.inject_start_variables(wf, variables or {})

    ticket = ApprovalTicket(
        title=title,
        project_id=project_id,
        task_id=task_id,
        definition_id=definition.id,
        definition_version=definition.version,
        submitted_by=submitted_by,
        variables=variables or {},
        status="running",
    )
    ticket.engine_state = bpmn_engine.save_state(wf)
    db.add(ticket)
    db.flush()
    _sync_tasks(db, ticket, wf)
    db.commit()
    db.refresh(ticket)
    return ticket


def complete_task(db: Session, approval_task: ApprovalTask, user: User,
                  action: str, comment: str = "") -> ApprovalTicket:
    if approval_task.status != "pending":
        raise HTTPException(400, "该审批任务已处理")
    if approval_task.assignee_id != user.id and not user.is_superuser:
        raise HTTPException(403, "只有任务负责人可以处理此审批")

    ticket = db.get(ApprovalTicket, approval_task.ticket_id)
    if not ticket or ticket.status != "running":
        raise HTTPException(400, "审批单已结束")

    wf = bpmn_engine.restore_state(ticket.engine_state)

    same_node_completed = (
        db.query(ApprovalTask)
        .filter(ApprovalTask.ticket_id == ticket.id,
                ApprovalTask.node_id == approval_task.node_id,
                ApprovalTask.status == "completed")
        .count()
    )
    total = len(_resolve_assignees(ticket.variables or {}, approval_task.node_id)) or None

    variables = {
        "approved": action == "approve",
        "rejected": action == "reject",
    }
    bpmn_engine.complete_user_task(
        wf, approval_task.engine_task_id, variables,
        completed_count=(same_node_completed + 1) if total else None,
        total_count=total,
    )

    approval_task.status = "completed"
    approval_task.action = action
    approval_task.comment = comment or ""
    from app.models import utcnow

    approval_task.finished_at = utcnow()

    _persist(db, ticket, wf)
    db.refresh(ticket)
    return ticket


def cancel_ticket(db: Session, ticket: ApprovalTicket, user: User) -> ApprovalTicket:
    if ticket.submitted_by != user.id and not user.is_superuser:
        raise HTTPException(403, "只有发起人可以撤回")
    if ticket.status != "running":
        raise HTTPException(400, "审批单已结束")
    ticket.status = "cancelled"
    from app.models import utcnow

    ticket.finished_at = utcnow()
    for row in db.query(ApprovalTask).filter(ApprovalTask.ticket_id == ticket.id,
                                             ApprovalTask.status == "pending"):
        row.status = "cancelled"
    db.commit()
    db.refresh(ticket)
    return ticket
