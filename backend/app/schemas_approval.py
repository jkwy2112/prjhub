from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import AuthType


class DefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    version: int
    is_active: bool
    has_tree: bool = False
    has_form: bool = False
    group_name: str = ""
    remark: str = ""
    logo: Optional[dict] = None
    created_at: datetime


class DefinitionDeploy(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(default="", max_length=128)
    bpmn_xml: str = Field(min_length=1)


class TreeDeploy(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(default="", max_length=128)
    tree: dict
    form_items: List[dict] = Field(default_factory=list)
    group_name: str = Field(default="默认分组", max_length=64)
    remark: str = Field(default="", max_length=500)
    logo: dict = Field(default_factory=dict)


class TicketCreate(BaseModel):
    definition_key: str
    title: str = Field(default="", max_length=255)  # 空则自动取流程名
    variables: dict = Field(default_factory=dict)
    project_id: Optional[int] = None
    task_id: Optional[int] = None


class ApprovalTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    node_id: str
    node_name: str
    assignee_id: Optional[int]
    status: str
    action: Optional[str]
    comment: str
    created_at: datetime
    finished_at: Optional[datetime]


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_no: str = ""
    title: str
    project_id: Optional[int]
    task_id: Optional[int]
    definition_id: int
    definition_key: str = ""
    definition_name: str = ""
    definition_version: int
    submitted_by: int
    variables: dict
    status: str
    created_at: datetime
    finished_at: Optional[datetime]


class TicketDetail(TicketOut):
    tasks: List[ApprovalTaskOut] = []
    my_pending_task_id: Optional[int] = None
    form_items: List[dict] = []
    form_values: dict = {}
    my_node_form_perms: dict = {}


class MyPendingOut(BaseModel):
    task_id: int
    node_name: str
    ticket: TicketOut


class ActionIn(BaseModel):
    action: str = Field(pattern=r"^(approve|reject)$")
    comment: str = Field(default="", max_length=2000)
