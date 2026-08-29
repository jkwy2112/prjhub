"""Approval business service: tickets, pending-task sync, actions. Engine-agnostic."""
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ApprovalTask, ApprovalTicket, ProcessDefinition, Project, Task, User
from app.services import bpmn_engine

logger = logging.getLogger(__name__)

GENERIC_KEY = "generic_approval"
PARALLEL_KEY = "parallel_approval"

# end event id -> ticket status
END_STATUS = {"end_approved": "approved", "end_rejected": "rejected"}


def deploy(db: Session, key: str, name: str, bpmn_xml: str,
           tree: Optional[dict] = None, node_meta: Optional[dict] = None) -> ProcessDefinition:
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
                                   bpmn_xml=bpmn_xml, tree=tree, node_meta=node_meta, is_active=True)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    logger.info("deployed process %s v%s", key, version)
    return definition


def deploy_tree(db: Session, key: str, name: str, tree: dict) -> ProcessDefinition:
    """Compile the designer tree and deploy (WFlow-style JSON as source of truth)."""
    from app.services import flow_compiler

    bpmn_xml, node_meta = flow_compiler.compile_tree(tree)
    # fixed members must reference existing users (clear config-time feedback)
    bad = sorted({
        uid
        for meta in node_meta.values()
        if meta.get("assigneeType") == "users"
        for uid in meta.get("users", [])
        if db.get(User, uid) is None
    })
    if bad:
        raise HTTPException(400, f"固定审批成员不存在: {bad}, 请重新选择")
    return deploy(db, key, name, bpmn_xml, tree=tree, node_meta=node_meta)


def seed_templates(db: Session) -> None:
    """Deploy built-in templates on first run; redeploy as a new version when XML changes."""
    from app.services.bpmn_templates import GENERIC_APPROVAL_BPMN, PARALLEL_APPROVAL_BPMN

    for key, name, xml in (
        (GENERIC_KEY, "通用审批流(条件金额分支/会签或签)", GENERIC_APPROVAL_BPMN),
        (PARALLEL_KEY, "并行多分支审批流(财务+技术同时审批/汇聚)", PARALLEL_APPROVAL_BPMN),
    ):
        current = (
            db.query(ProcessDefinition)
            .filter(ProcessDefinition.key == key, ProcessDefinition.is_active.is_(True))
            .order_by(ProcessDefinition.version.desc())
            .first()
        )
        if current is None or current.bpmn_xml != xml:
            deploy(db, key, name, xml)


def active_definition(db: Session, key: str) -> ProcessDefinition:
    definition = (
        db.query(ProcessDefinition)
        .filter(ProcessDefinition.key == key, ProcessDefinition.is_active.is_(True))
        .first()
    )
    if not definition:
        raise HTTPException(404, f"流程定义 {key} 不存在")
    return definition


def _definition_of(db: Session, ticket: ApprovalTicket) -> ProcessDefinition:
    return db.get(ProcessDefinition, ticket.definition_id)


def _resolve_assignees(db: Session, ticket: ApprovalTicket, node_id: str) -> list:
    """Priority: designed node_meta (fixed members / runtime variable) > legacy conventions.

    Nonexistent users are filtered out defensively (e.g. member deleted after design)."""
    definition = _definition_of(db, ticket)
    meta = (definition.node_meta or {}).get(node_id) if definition else None
    if meta:
        if meta.get("assigneeType") == "runtime":
            value = (ticket.variables or {}).get(f"approver_{node_id}") or []
            users = list(value)
        else:
            users = list(meta.get("users") or [])
    else:
        variables = ticket.variables or {}
        if node_id == "ut_cs":
            users = list(variables.get("countersigners") or [])
        else:
            short = node_id[3:] if node_id.startswith("ut_") else node_id
            value = variables.get(f"approver_{short}", variables.get(f"approver_{node_id}"))
            users = [value] if value else []
    if not users:
        return []
    rows = db.query(User.id).filter(User.id.in_(users), User.is_active.is_(True)).all()
    valid = {r[0] for r in rows}
    return [u for u in users if u in valid]


def _start_variables(definition: ProcessDefinition, ticket_vars: dict) -> dict:
    """Runtime-designed multi-instance nodes need cardinality/pass variables at start."""
    extras: dict = {}
    for tid, meta in (definition.node_meta or {}).items():
        if meta.get("assigneeType") != "runtime":
            continue
        users = ticket_vars.get(f"approver_{tid}") or []
        if not users:
            raise HTTPException(400, f"流程要求指定「{meta.get('name') or tid}」的审批人(approver_{tid})")
        extras[f"assignee_total_{tid}"] = len(users)
        if meta.get("mode") == "count":
            extras[f"pass_{tid}"] = min(int(meta.get("count") or 1), len(users))
    return extras


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
        candidates = _resolve_assignees(db, ticket, et.node_id)
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

    start_vars = dict(variables or {})
    start_vars.update(_start_variables(definition, variables or {}))
    wf = bpmn_engine.start_workflow(definition.bpmn_xml, variables=start_vars)

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
    candidates = _resolve_assignees(db, ticket, approval_task.node_id)
    total = len(candidates) or None

    variables = {
        "approved": action == "approve",
        "rejected": action == "reject",
    }
    # designed runtime nodes: inject pass_<tid> for count-mode completion expressions
    definition = _definition_of(db, ticket)
    meta = (definition.node_meta or {}).get(approval_task.node_id) if definition else None
    if meta and meta.get("assigneeType") == "runtime" and meta.get("mode") == "count":
        variables[f"pass_{approval_task.node_id}"] = min(int(meta.get("count") or 1), total or 1)

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
