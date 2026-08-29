"""Engine adapter layer - the ONLY module importing SpiffWorkflow.

Business code (approval_service) talks to this module only, so the engine can be
swapped later without touching business logic.
"""
import io
import logging
from typing import Optional
from uuid import UUID

from SpiffWorkflow import TaskState
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow

logger = logging.getLogger(__name__)

_serializer = BpmnWorkflowSerializer()


class EngineError(Exception):
    pass


def parse_spec(bpmn_xml: str, process_id: Optional[str] = None):
    parser = BpmnParser()
    try:
        parser.add_bpmn_io(io.BytesIO(bpmn_xml.encode("utf-8")), "definition.bpmn")
    except Exception as exc:
        raise EngineError(f"BPMN 解析失败: {exc}") from exc
    try:
        return parser.get_spec(process_id) if process_id else parser.get_spec(parser.get_process_ids()[0])
    except Exception as exc:
        raise EngineError(f"BPMN 流程校验失败: {exc}") from exc


def start_workflow(bpmn_xml: str, process_id: Optional[str] = None) -> BpmnWorkflow:
    wf = BpmnWorkflow(parse_spec(bpmn_xml, process_id))
    wf.do_engine_steps()
    return wf


def save_state(wf: BpmnWorkflow) -> bytes:
    return _serializer.serialize_json(wf).encode("utf-8")


def restore_state(state: bytes) -> BpmnWorkflow:
    return _serializer.deserialize_json(state.decode("utf-8"))


class EngineUserTask:
    """View model of a READY user task instance."""

    __slots__ = ("engine_task_id", "node_id", "node_name", "data", "is_multiinstance")

    def __init__(self, engine_task_id, node_id, node_name, data, is_multiinstance):
        self.engine_task_id = engine_task_id
        self.node_id = node_id
        self.node_name = node_name
        self.data = data
        self.is_multiinstance = is_multiinstance


def ready_user_tasks(wf: BpmnWorkflow) -> "list[EngineUserTask]":
    out = []
    for t in wf.get_tasks(state=TaskState.READY):
        spec = t.task_spec
        if not getattr(spec, "manual", False):
            continue
        node_id = getattr(spec, "bpmn_id", None) or spec.name
        out.append(EngineUserTask(
            engine_task_id=str(t.id),
            node_id=node_id,
            node_name=getattr(spec, "bpmn_name", None) or spec.name,
            data=t.data,
            is_multiinstance=t.internal_data.get("key_or_index") is not None,
        ))
    return out


def complete_user_task(wf: BpmnWorkflow, engine_task_id: str, variables: dict,
                       completed_count: Optional[int] = None, total_count: Optional[int] = None) -> None:
    """Complete one user task; variables are injected into its task data (expression scope)."""
    task = wf.get_task_from_id(UUID(engine_task_id))
    if task is None:
        raise EngineError("任务在流程中不存在或已处理")
    from SpiffWorkflow import TaskState as _TS

    if not task.has_state(_TS.READY):
        raise EngineError("任务当前不可处理")
    data = dict(variables)
    if completed_count is not None:
        data["completed_count"] = completed_count
    if total_count is not None:
        data["total_count"] = total_count
    task.data.update(data)
    wf.run_task_from_id(task.id)
    wf.do_engine_steps()


def reached_end(wf: BpmnWorkflow) -> Optional[str]:
    """Return the bpmn_id of the reached end event, or None if still running."""
    if not wf.is_completed():
        return None
    for t in wf.get_tasks(state=TaskState.COMPLETED):
        spec = t.task_spec
        bpmn_id = getattr(spec, "bpmn_id", None) or ""
        if spec.__class__.__name__ == "BpmnEndEvent" or bpmn_id.startswith("end"):
            return bpmn_id or spec.name
    return "end"


def inject_start_variables(wf: BpmnWorkflow, variables: dict) -> None:
    """Put process variables into the first ready user task's data (expression scope)."""
    for t in wf.get_tasks(state=TaskState.READY):
        if getattr(t.task_spec, "manual", False):
            t.data.update(variables)
            return
    # no user task ready yet (edge case): store on workflow data as fallback
    wf.data.update(variables)
