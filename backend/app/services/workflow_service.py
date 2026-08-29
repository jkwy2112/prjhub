"""Multi-workflow engine: definitions, node validation, handler rules, task migration.

Reference model (Jira-like):
- admin manages multiple Workflow definitions, each has status nodes + transition edges
- a project binds to one workflow (null = system default workflow)
- a node may restrict WHO can move a task INTO it (handler rules)
"""
import re
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, ProjectRole, Task, User, Workflow, WorkflowNode

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# default workflow layout (left -> right canvas)
DEFAULT_WORKFLOW = [
    {"key": "todo", "name": "待办", "color": "#909399", "x": 60, "y": 200,
     "is_initial": True, "is_done": False, "next_keys": ["in_progress", "done"],
     "handler_type": "any", "handler_user_ids": []},
    {"key": "in_progress", "name": "进行中", "color": "#409EFF", "x": 340, "y": 200,
     "is_initial": False, "is_done": False, "next_keys": ["testing", "done"],
     "handler_type": "any", "handler_user_ids": []},
    {"key": "testing", "name": "测试中", "color": "#E6A23C", "x": 620, "y": 200,
     "is_initial": False, "is_done": False, "next_keys": ["in_progress", "done"],
     "handler_type": "any", "handler_user_ids": []},
    {"key": "done", "name": "已完成", "color": "#67C23A", "x": 900, "y": 200,
     "is_initial": False, "is_done": True, "next_keys": ["todo"],
     "handler_type": "any", "handler_user_ids": []},
]

HANDLER_TYPES = {"any", "assignee", "admins", "members"}


# ---------- workflow CRUD ----------


def seed_default_workflow(db: Session) -> None:
    if db.query(Workflow).count() == 0:
        create_workflow(db, name="默认工作流", description="系统默认: 待办 → 进行中 → 测试中 → 已完成",
                        nodes=DEFAULT_WORKFLOW, is_default=True)


def create_workflow(db: Session, name: str, description: str = "", nodes=None,
                    is_default: bool = False) -> Workflow:
    if db.query(Workflow).filter(Workflow.name == name).first():
        raise HTTPException(400, f"工作流「{name}」已存在")
    if is_default:
        db.query(Workflow).filter(Workflow.is_default.is_(True)).update({"is_default": False})
    wf = Workflow(name=name, description=description, is_default=is_default)
    db.add(wf)
    db.flush()
    replace_nodes(db, wf, nodes or DEFAULT_WORKFLOW)
    db.commit()
    db.refresh(wf)
    return wf


def get_or_404(db: Session, workflow_id: int) -> Workflow:
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "工作流不存在")
    return wf


def default_workflow(db: Session) -> Workflow:
    wf = db.query(Workflow).filter(Workflow.is_default.is_(True)).first()
    if wf:
        return wf
    seed_default_workflow(db)
    return db.query(Workflow).filter(Workflow.is_default.is_(True)).first()


def project_workflow(db: Session, project: Project) -> Workflow:
    if project.workflow_id:
        wf = db.get(Workflow, project.workflow_id)
        if wf:
            return wf
    return default_workflow(db)


def list_workflows(db: Session) -> "list[dict]":
    out = []
    for wf in db.query(Workflow).order_by(Workflow.id).all():
        out.append({
            "id": wf.id, "name": wf.name, "description": wf.description,
            "is_default": wf.is_default, "node_count": len(wf.nodes),
            "project_count": db.query(Project).filter(Project.workflow_id == wf.id).count(),
        })
    return out


def workflow_payload(wf: Workflow) -> dict:
    return {
        "id": wf.id, "name": wf.name, "description": wf.description, "is_default": wf.is_default,
        "nodes": [
            {"id": n.id, "key": n.key, "name": n.name, "color": n.color, "x": n.x, "y": n.y,
             "is_initial": n.is_initial, "is_done": n.is_done, "next_keys": n.next_keys or [],
             "handler_type": n.handler_type or "any", "handler_user_ids": n.handler_user_ids or []}
            for n in wf.nodes
        ],
    }


# ---------- nodes validation & save ----------


def _validate_nodes(nodes: "list[dict]") -> None:
    if not nodes:
        raise HTTPException(400, "至少需要一个状态节点")
    keys = [n["key"] for n in nodes]
    if len(set(keys)) != len(keys):
        raise HTTPException(400, "节点标识不能重复")
    for n in nodes:
        if not KEY_PATTERN.match(n["key"]):
            raise HTTPException(400, f"节点标识 {n['key']} 不合法 (小写字母开头, 仅 a-z0-9_)")
        if not str(n["name"]).strip():
            raise HTTPException(400, "节点名称不能为空")
        if n.get("handler_type") not in HANDLER_TYPES:
            raise HTTPException(400, f"处理人规则 {n.get('handler_type')} 不合法")
        for nk in n.get("next_keys") or []:
            if nk not in keys:
                raise HTTPException(400, f"「{n['name']}」的流转目标 {nk} 不存在")
            if nk == n["key"]:
                raise HTTPException(400, f"「{n['name']}」不能流转到自身")
    initials = [n for n in nodes if n.get("is_initial")]
    if len(initials) != 1:
        raise HTTPException(400, "必须且只能有一个初始状态")


def replace_nodes(db: Session, wf: Workflow, nodes: "list[dict]") -> int:
    """Replace all nodes. Tasks in projects bound to this workflow that sit on removed
    statuses are migrated to the new initial status. Returns migrated count."""
    _validate_nodes(nodes)
    incoming = {n["key"] for n in nodes}
    initial = next(n["key"] for n in nodes if n["is_initial"])

    migrated = 0
    project_ids = [p.id for p in db.query(Project).filter(Project.workflow_id == wf.id).all()]
    if wf.is_default:
        # projects without explicit binding also follow the default workflow
        project_ids += [p.id for p in db.query(Project).filter(Project.workflow_id.is_(None)).all()]
        project_ids = list(set(project_ids))
    for pid in project_ids:
        migrated += (
            db.query(Task)
            .filter(Task.project_id == pid, Task.status.notin_(incoming) | Task.status.is_(None))
            .update({Task.status: initial}, synchronize_session=False)
        )

    db.query(WorkflowNode).filter(WorkflowNode.workflow_id == wf.id).delete()
    db.flush()
    for idx, n in enumerate(nodes, start=1):
        db.add(WorkflowNode(
            workflow_id=wf.id, key=n["key"], name=str(n["name"]).strip(),
            color=n.get("color") or "#409EFF",
            x=int(n.get("x") or 0), y=int(n.get("y") or 0),
            sort_order=idx, is_initial=bool(n.get("is_initial")), is_done=bool(n.get("is_done")),
            next_keys=[k for k in (n.get("next_keys") or [])],
            handler_type=n.get("handler_type") or "any",
            handler_user_ids=[int(u) for u in (n.get("handler_user_ids") or [])],
        ))
    return migrated


def save_workflow(db: Session, wf: Workflow, name: str, description: str, nodes) -> int:
    if name != wf.name and db.query(Workflow).filter(Workflow.name == name).first():
        raise HTTPException(400, f"工作流「{name}」已存在")
    wf.name = name
    wf.description = description
    migrated = replace_nodes(db, wf, nodes)
    db.commit()
    return migrated


def delete_workflow(db: Session, wf: Workflow) -> None:
    if wf.is_default:
        raise HTTPException(400, "默认工作流不能删除")
    bound = db.query(Project).filter(Project.workflow_id == wf.id).count()
    if bound:
        raise HTTPException(400, f"仍有 {bound} 个项目绑定该工作流, 请先在项目设置中解绑")
    db.delete(wf)
    db.commit()


# ---------- runtime helpers ----------


def node_map(wf: Workflow) -> "dict[str, WorkflowNode]":
    return {n.key: n for n in wf.nodes}


def initial_key(wf: Workflow) -> str:
    for n in wf.nodes:
        if n.is_initial:
            return n.key
    return wf.nodes[0].key if wf.nodes else ""


def done_keys(wf: Workflow) -> "list[str]":
    return [n.key for n in wf.nodes if n.is_done]


def can_transition(wf: Workflow, current: str, target: str) -> bool:
    node = node_map(wf).get(current)
    return bool(node and target in (node.next_keys or []) and target != current)


def can_handle(db: Session, wf: Workflow, target_key: str, user: User,
               project: Project, task: Optional[Task] = None) -> "tuple[bool, str]":
    """Whether `user` may move a task INTO target node (handler rules; superuser bypasses)."""
    if user.is_superuser:
        return True, ""
    node = node_map(wf).get(target_key)
    if node is None:
        return False, "目标状态不存在"
    htype = node.handler_type or "any"
    if htype == "any":
        return True, ""
    if htype == "assignee":
        if task and task.assignee_id == user.id:
            return True, ""
        return False, f"仅任务负责人可流转到「{node.name}」"
    if htype == "admins":
        member = (db.query(ProjectMember)
                  .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
                  .first())
        if member and member.role in (ProjectRole.owner, ProjectRole.admin):
            return True, ""
        return False, f"仅项目管理员可流转到「{node.name}」"
    if htype == "members":
        if user.id in (node.handler_user_ids or []):
            return True, ""
        names = [
            (u.name or u.username) for u in
            db.query(User).filter(User.id.in_(node.handler_user_ids or [])).all()
        ] if node.handler_user_ids else []
        who = "、".join(names[:5]) or "未配置"
        return False, f"「{node.name}」仅限 {who} 处理"
    return True, ""


def handler_summary(db: Session, node: WorkflowNode) -> str:
    htype = node.handler_type or "any"
    if htype == "any":
        return "任何人"
    if htype == "assignee":
        return "任务负责人"
    if htype == "admins":
        return "项目管理员"
    if htype == "members":
        users = db.query(User).filter(User.id.in_(node.handler_user_ids or [])).all()
        return "指定成员: " + "、".join((u.name or u.username) for u in users) if users else "指定成员: (未配置)"
    return htype
