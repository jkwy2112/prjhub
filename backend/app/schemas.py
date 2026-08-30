from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import AuthType, ProjectRole, TaskPriority, TaskType


# ---------- auth ----------


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class WeComAuthRequest(BaseModel):
    code: str


# ---------- user ----------


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    dept: str = ""
    email: str
    avatar: str
    auth_type: AuthType
    is_active: bool
    is_superuser: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


# ---------- project ----------


class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    color: str = "#409EFF"
    init_git_repo: bool = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_archived: Optional[bool] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str
    color: str
    repo_path: str
    is_archived: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    task_count: int = 0
    my_role: Optional[ProjectRole] = None


class MemberAdd(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.member


class MemberUpdate(BaseModel):
    role: ProjectRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    joined_at: datetime
    user: UserOut


# ---------- task ----------


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    type: TaskType = TaskType.task
    priority: TaskPriority = TaskPriority.medium
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TaskType] = None
    status: Optional[str] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    task_order: Optional[int] = None


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserOut


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title: str
    description: str
    type: TaskType
    status: str
    priority: TaskPriority
    assignee_id: Optional[int]
    project_id: int
    created_by: int
    due_date: Optional[datetime]
    task_order: int
    created_at: datetime
    updated_at: datetime
    comments_count: int = 0


class TaskDetail(TaskOut):
    comments: List[CommentOut] = []


# ---------- activity ----------


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: Optional[int]
    task_id: Optional[int]
    user_id: Optional[int]
    action: str
    target: str
    detail: dict
    created_at: datetime
    user: Optional[UserOut]


# ---------- dashboard ----------


class DashboardOut(BaseModel):
    project_count: int
    my_open_task_count: int
    overdue_task_count: int
    done_task_count: int
    status_distribution: dict
    type_distribution: dict
    my_recent_tasks: List[TaskOut]
    recent_activities: List[ActivityOut]


TokenResponse.model_rebuild()
