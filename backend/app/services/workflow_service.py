"""Customizable workflow: statuses, transition rules, validation."""
import re
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Task, WorkflowStatus

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

DEFAULT_WORKFLOW = [
    {"key": "todo", "name": "待办", "color": "#909399", "sort_order": 1,
     "is_initial": True, "is_done": False, "next_keys": ["in_progress", "done"]},
    {"key": "in_progress", "name": "进行中", "color": "#409EFF", "sort_order": 2,
     "is_initial": False, "is_done": False, "next_keys": ["todo", "testing", "done"]},
    {"key": "testing", "name": "测试中", "color": "#E6A23C", "sort_order": 3,
     "is_initial": False, "is_done": False, "next_keys": ["in_progress", "done"]},
    {"key": "done", "name": "已完成", "color": "#67C23A", "sort_order": 4,
     "is_initial": False, "is_done": True, "next_keys": ["todo"]},
]


def seed_workflow(db: Session) -> None:
    if db.query(WorkflowStatus).count() == 0:
        reset_to_default(db)


def reset_to_default(db: Session) -> List[WorkflowStatus]:
    _migrate_orphans(db, {d["key"] for d in DEFAULT_WORKFLOW},
                     next(d["key"] for d in DEFAULT_WORKFLOW if d["is_initial"]))
    db.query(WorkflowStatus).delete()
    db.flush()
    for item in DEFAULT_WORKFLOW:
        db.add(WorkflowStatus(**item))
    db.commit()
    return get_statuses(db)


def _migrate_orphans(db: Session, incoming_keys: "set[str]", initial: str) -> int:
    """Tasks sitting on statuses that no longer exist are moved to the initial status."""
    orphans = [
        row[0] for row in db.query(Task.status).distinct().all()
        if row[0] and row[0] not in incoming_keys
    ]
    moved = 0
    for key in orphans:
        moved += (
            db.query(Task)
            .filter(Task.status == key)
            .update({Task.status: initial}, synchronize_session=False)
        )
    return moved


def get_statuses(db: Session) -> List[WorkflowStatus]:
    return db.query(WorkflowStatus).order_by(WorkflowStatus.sort_order, WorkflowStatus.id).all()


def initial_key(db: Session) -> str:
    s = db.query(WorkflowStatus).filter(WorkflowStatus.is_initial.is_(True)).first()
    return s.key if s else ""


def done_keys(db: Session) -> "list[str]":
    return [s.key for s in db.query(WorkflowStatus).filter(WorkflowStatus.is_done.is_(True)).all()]


def status_map(db: Session) -> "dict[str, WorkflowStatus]":
    return {s.key: s for s in get_statuses(db)}


def can_transition(db: Session, current: str, target: str) -> bool:
    if current == target:
        return False
    s = db.query(WorkflowStatus).filter(WorkflowStatus.key == current).first()
    return bool(s and target in (s.next_keys or []))


def _validate(db: Session, payload: "list[dict]") -> None:
    if not payload:
        raise HTTPException(400, "至少需要一个工作流状态")
    keys = [p["key"] for p in payload]
    if len(set(keys)) != len(keys):
        raise HTTPException(400, "状态标识不能重复")
    for p in payload:
        if not KEY_PATTERN.match(p["key"]):
            raise HTTPException(400, f"状态标识 {p['key']} 不合法 (小写字母开头, 仅 a-z0-9_)")
        if not p["name"].strip():
            raise HTTPException(400, "状态名称不能为空")
        if len(p["name"]) > 32:
            raise HTTPException(400, "状态名称最长 32 字符")
        for nk in p["next_keys"]:
            if nk not in keys:
                raise HTTPException(400, f"「{p['name']}」的可流转目标 {nk} 不存在")
            if nk == p["key"]:
                raise HTTPException(400, f"「{p['name']}」不能流转到自身")
    initials = [p for p in payload if p["is_initial"]]
    if len(initials) != 1:
        raise HTTPException(400, "必须且只能有一个初始状态")


def save_workflow(db: Session, payload: "list[dict]") -> "tuple[List[WorkflowStatus], int]":
    """Full replace. Tasks on dropped statuses are migrated to the initial status.

    Returns (statuses, migrated_count).
    """
    _validate(db, payload)
    incoming_keys = {p["key"] for p in payload}
    initial = next(p["key"] for p in payload if p["is_initial"])
    migrated = _migrate_orphans(db, incoming_keys, initial)

    db.query(WorkflowStatus).delete()
    db.flush()
    for idx, p in enumerate(payload, start=1):
        db.add(WorkflowStatus(
            key=p["key"], name=p["name"].strip(), color=p.get("color") or "#409EFF",
            sort_order=idx, is_initial=p["is_initial"], is_done=p["is_done"],
            next_keys=p.get("next_keys") or [],
        ))
    db.commit()
    return get_statuses(db), migrated
