import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthType(str, enum.Enum):
    local = "local"
    ldap = "ldap"
    wecom = "wecom"


class ProjectRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class TaskType(str, enum.Enum):
    requirement = "requirement"
    task = "task"
    bug = "bug"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    testing = "testing"
    done = "done"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SystemConfig(Base):
    """Runtime-editable system configuration (auth etc.), overlays .env settings."""
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------- BPMN approval engine (SpiffWorkflow) ----------


class ProcessDefinition(Base):
    """Versioned BPMN process definition. Latest version of a key is active.

    A definition is either hand-written BPMN (bpmn_xml only) or designed as a
    nested tree in the visual designer (tree + compiled bpmn_xml + node_meta).
    """
    __tablename__ = "process_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    bpmn_xml: Mapped[str] = mapped_column(Text)
    tree: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)          # designer source
    node_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)     # bpmn_id -> runtime meta
    form_items: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)    # form designer source
    group_name: Mapped[str] = mapped_column(String(64), default="默认分组")
    remark: Mapped[str] = mapped_column(String(500), default="")
    logo: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)          # {icon, background}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalTicket(Base):
    """An approval request running on a (pinned) process definition version."""
    __tablename__ = "approval_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_no: Mapped[str] = mapped_column(String(32), default="", index=True)  # 审批编号 e.g. 20260830153012
    title: Mapped[str] = mapped_column(String(255))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"),
                                                      nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"),
                                                   nullable=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("process_definitions.id"))
    definition_version: Mapped[int] = mapped_column(Integer, default=1)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    engine_state: Mapped[bytes] = mapped_column(LargeBinary)  # serialized BpmnWorkflow
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)  # running/approved/rejected/cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[List["ApprovalTask"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="ApprovalTask.id"
    )


class ApprovalTask(Base):
    """Mirror of an engine user task: pending todo or audit record once completed."""
    __tablename__ = "approval_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("approval_tickets.id", ondelete="CASCADE"), index=True)
    engine_task_id: Mapped[str] = mapped_column(String(64), index=True)
    node_id: Mapped[str] = mapped_column(String(64), default="")
    node_name: Mapped[str] = mapped_column(String(128), default="")
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                       nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending/completed/cancelled
    action: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # approve/reject/cc/remind
    comment: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)      # timeout deadline
    reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # last reminder
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    ticket: Mapped[ApprovalTicket] = relationship(back_populates="tasks")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), default="")
    name: Mapped[str] = mapped_column(String(128), default="")
    dept: Mapped[str] = mapped_column(String(128), default="")
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    avatar: Mapped[str] = mapped_column(String(512), default="")
    auth_type: Mapped[AuthType] = mapped_column(Enum(AuthType), default=AuthType.local)
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)  # wecom userid / ldap dn
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped["ProjectMember"] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        return self.name or self.username


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # e.g. PRJ, task key prefix
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="#409EFF")
    repo_path: Mapped[str] = mapped_column(String(512), default="")  # auto-initialized git repo
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    members: Mapped["ProjectMember"] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped["Task"] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole), default=ProjectRole.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, default=0)  # per-project sequence, e.g. PRJ-12
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[TaskType] = mapped_column(Enum(TaskType), default=TaskType.task)
    status: Mapped[str] = mapped_column(String(32), default="", index=True)  # WorkflowStatus.key
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.medium)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    task_order: Mapped[int] = mapped_column(Integer, default=0)  # order inside kanban column
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assignee_id])
    comments: Mapped[List["Comment"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    @property
    def task_key(self) -> str:
        return f"{self.project.key}-{self.number}"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[Task] = relationship(back_populates="comments")
    user: Mapped[User] = relationship()


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))       # create / update / comment / delete / join ...
    target: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[Optional["User"]] = relationship()
