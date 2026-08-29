"""Tree -> BPMN compiler tests: validation + engine runs on compiled output."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from app.services import bpmn_engine, flow_compiler  # noqa: E402


def _approval(name="审批", users=(1,), mode="any", count=0, assignee_type="users", child=None):
    return {"type": "APPROVAL", "name": name,
            "props": {"assigneeType": assignee_type, "users": list(users), "mode": mode, "count": count},
            "childNode": child}


def _cond(field="amount", compare=">", value=(1000,)):
    return {"field": field, "compare": compare, "value": list(value)}


def _conditions(branches, child=None):
    return {"type": "CONDITIONS", "name": "条件分支", "branches": branches, "childNode": child}


def _concurrents(branches, child=None):
    return {"type": "CONCURRENTS", "name": "并行分支", "branches": branches, "childNode": child}


def _run(xml, actions, variables=None):
    """actions: list of (expected_node_names, action_or_None) driven step by step."""
    wf = bpmn_engine.start_workflow(xml, variables=variables or {})
    for expect_names, action in actions:
        ready = bpmn_engine.ready_user_tasks(wf)
        assert sorted(t.node_name for t in ready) == sorted(expect_names), \
            f"expect {expect_names}, got {[t.node_name for t in ready]}"
        if action:
            for idx, t in enumerate(ready, start=1):
                bpmn_engine.complete_user_task(wf, t.engine_task_id,
                                               {"approved": action == "approve", "rejected": action == "reject"},
                                               completed_count=idx, total_count=len(ready) or 1)
    return wf


def test_compile_simple_chain():
    tree = {"type": "ROOT", "childNode": _approval("一级", users=(1,), child=_approval("二级", users=(2,)))}
    xml, meta = flow_compiler.compile_tree(tree)
    assert len([k for k in meta if k.startswith("ut_ap")]) == 2
    wf = _run(xml, [(["一级"], "approve"), (["二级"], "approve")])
    assert wf.is_completed()
    assert bpmn_engine.reached_end(wf) == "end_approved"


def test_compile_reject_routes_to_terminate():
    tree = {"type": "ROOT", "childNode": _approval("一级", users=(1,), child=_approval("二级", users=(2,)))}
    xml, _ = flow_compiler.compile_tree(tree)
    wf = _run(xml, [(["一级"], "reject")])
    assert wf.is_completed()
    assert bpmn_engine.reached_end(wf) == "end_rejected"


def test_compile_conditions_route_by_variable():
    tree = {"type": "ROOT", "childNode": _conditions([
        {"type": "CONDITION", "name": "大额", "props": {"groups": [{"groupType": "AND", "conditions": [_cond()]}]},
         "childNode": _approval("财务", users=(9,))},
        {"type": "CONDITION", "name": "默认", "props": {"groups": []}, "childNode": _approval("主管", users=(8,))},
    ], child=_approval("归档", users=(7,)))}
    xml, meta = flow_compiler.compile_tree(tree)
    assert len(meta) == 3

    # big amount -> 财务 -> 归档
    wf = _run(xml, [(["财务"], "approve"), (["归档"], "approve")], {"amount": 5000})
    assert bpmn_engine.reached_end(wf) == "end_approved"

    # small amount -> default 主管 -> 归档
    wf2 = _run(xml, [(["主管"], "approve"), (["归档"], "approve")], {"amount": 100})
    assert bpmn_engine.reached_end(wf2) == "end_approved"


def test_compile_condition_groups_and_or():
    tree = {"type": "ROOT", "childNode": _conditions([
        {"type": "CONDITION", "name": "复杂", "props": {"groupsType": "OR", "groups": [
            {"groupType": "AND", "conditions": [_cond("amount", ">", [2000]), _cond("level", "==", [3])]},
            {"groupType": "OR", "conditions": [_cond("amount", "between", [100, 200])]},
        ]}, "childNode": _approval("A", users=(1,))},
        {"type": "CONDITION", "name": "默认", "props": {"groups": []}, "childNode": _approval("B", users=(2,))},
    ])}
    xml, _ = flow_compiler.compile_tree(tree)
    _run(xml, [(["A"], "approve")], {"amount": 5000, "level": 3})
    _run(xml, [(["A"], "approve")], {"amount": 150})
    _run(xml, [(["B"], "approve")], {"amount": 5000, "level": 1})


def test_compile_concurrents_join_waits_all():
    tree = {"type": "ROOT", "childNode": _concurrents([
        {"type": "BRANCH", "name": "财务线", "childNode": _approval("财务", users=(1,))},
        {"type": "BRANCH", "name": "技术线", "childNode": _approval("技术", users=(2,))},
    ], child=_approval("终审", users=(3,)))}
    xml, _ = flow_compiler.compile_tree(tree)

    wf = bpmn_engine.start_workflow(xml)
    bpmn_engine.inject_start_variables(wf, {})
    ready = {t.node_name: t for t in bpmn_engine.ready_user_tasks(wf)}
    assert set(ready) == {"财务", "技术"}
    bpmn_engine.complete_user_task(wf, ready["财务"].engine_task_id, {"approved": True, "rejected": False}, 1, 1)
    left = bpmn_engine.ready_user_tasks(wf)
    assert [t.node_name for t in left] == ["技术"]  # join waits
    bpmn_engine.complete_user_task(wf, left[0].engine_task_id, {"approved": True, "rejected": False}, 1, 1)
    final = bpmn_engine.ready_user_tasks(wf)
    assert [t.node_name for t in final] == ["终审"]
    bpmn_engine.complete_user_task(wf, final[0].engine_task_id, {"approved": True, "rejected": False}, 1, 1)
    assert bpmn_engine.reached_end(wf) == "end_approved"


def test_compile_countersign_or_sign():
    tree = {"type": "ROOT", "childNode": _approval("会签", users=(1, 2, 3), mode="count", count=2)}
    xml, meta = flow_compiler.compile_tree(tree)
    (tid,) = [k for k in meta]
    assert meta[tid]["mode"] == "count"

    wf = bpmn_engine.start_workflow(xml)
    bpmn_engine.inject_start_variables(wf, {})
    ready = bpmn_engine.ready_user_tasks(wf)
    assert len(ready) == 3
    # 1st/2nd approve (completed_count 1,2) -> completion >= 2 reached at 2nd
    bpmn_engine.complete_user_task(wf, ready[0].engine_task_id,
                                   {"approved": True, "rejected": False}, 1, 3)
    bpmn_engine.complete_user_task(wf, ready[1].engine_task_id,
                                   {"approved": True, "rejected": False}, 2, 3)
    assert wf.is_completed()
    assert bpmn_engine.reached_end(wf) == "end_approved"


def test_compile_reject_during_countersign_terminates():
    tree = {"type": "ROOT", "childNode": _approval("会签", users=(1, 2, 3), mode="all")}
    xml, _ = flow_compiler.compile_tree(tree)
    wf = bpmn_engine.start_workflow(xml)
    bpmn_engine.inject_start_variables(wf, {})
    ready = bpmn_engine.ready_user_tasks(wf)
    bpmn_engine.complete_user_task(wf, ready[0].engine_task_id,
                                   {"approved": False, "rejected": True}, 1, 3)
    assert wf.is_completed()  # completion condition: >= total OR rejected
    assert bpmn_engine.reached_end(wf) == "end_rejected"


def test_compile_nested_branch_in_branch():
    inner = _conditions([
        {"type": "CONDITION", "name": "加急", "props": {"groups": [{"groupType": "AND",
                                                                   "conditions": [_cond("urgent", "==", [1])]}]},
         "childNode": _approval("加急审批", users=(5,))},
        {"type": "CONDITION", "name": "普通", "props": {"groups": []}, "childNode": _approval("普通审批", users=(6,))},
    ])
    tree = {"type": "ROOT", "childNode": _conditions([
        {"type": "CONDITION", "name": "大额", "props": {"groups": [{"groupType": "AND",
                                                                    "conditions": [_cond()]}]},
         "childNode": inner},
        {"type": "CONDITION", "name": "小额", "props": {"groups": []}, "childNode": _approval("主管", users=(8,))},
    ])}
    xml, _ = flow_compiler.compile_tree(tree)
    _run(xml, [(["加急审批"], "approve")], {"amount": 9000, "urgent": 1})
    _run(xml, [(["普通审批"], "approve")], {"amount": 9000, "urgent": 0})
    _run(xml, [(["主管"], "approve")], {"amount": 10})


def test_compile_runtime_assignees():
    tree = {"type": "ROOT", "childNode": _approval("动态审批", users=[], assignee_type="runtime", mode="count",
                                                   count=2)}
    xml, meta = flow_compiler.compile_tree(tree)
    tid = next(k for k in meta)
    assert meta[tid]["assigneeType"] == "runtime"

    wf = bpmn_engine.start_workflow(xml, variables={f"assignee_total_{tid}": 3})
    ready = bpmn_engine.ready_user_tasks(wf)
    assert len(ready) == 3
    extra = {f"pass_{tid}": 2}
    bpmn_engine.complete_user_task(wf, ready[0].engine_task_id,
                                   {"approved": True, "rejected": False, **extra}, 1, 3)
    bpmn_engine.complete_user_task(wf, ready[1].engine_task_id,
                                   {"approved": True, "rejected": False, **extra}, 2, 3)
    assert wf.is_completed()
    assert bpmn_engine.reached_end(wf) == "end_approved"


def test_compile_validation_errors():
    from app.services.flow_compiler import FlowCompileError

    with pytest.raises(FlowCompileError):
        flow_compiler.compile_tree({"type": "ROOT"})  # empty
    with pytest.raises(FlowCompileError):
        flow_compiler.compile_tree({"type": "ROOT", "childNode": _approval("无审批人", users=[])})
    with pytest.raises(FlowCompileError):
        flow_compiler.compile_tree({"type": "ROOT", "childNode": _conditions([
            {"type": "CONDITION", "name": "A", "props": {"groups": [
                {"groupType": "AND", "conditions": [{"field": "amount", "compare": ">", "value": []}]}]}},
            {"type": "CONDITION", "name": "B", "props": {"groups": []}},
        ])})
    with pytest.raises(FlowCompileError):
        flow_compiler.compile_tree({"type": "ROOT", "childNode": _concurrents([
            {"type": "BRANCH", "childNode": _approval("单分支", users=(1,))},
        ])})
    with pytest.raises(FlowCompileError):
        flow_compiler.compile_tree({"type": "ROOT", "childNode": {
            "type": "UNKNOWN", "props": {}, "childNode": None}})


def test_compile_string_and_array_conditions():
    tree = {"type": "ROOT", "childNode": _conditions([
        {"type": "CONDITION", "name": "文本", "props": {"groups": [
            {"groupType": "AND", "conditions": [
                {"field": "reason", "valueType": "String", "compare": "==", "value": ["紧急"]},
                {"field": "tags", "valueType": "Array", "compare": "in", "value": ["加急", "特急"]},
            ]}]},
            "childNode": _approval("A", users=(1,))},
        {"type": "CONDITION", "name": "默认", "props": {"groups": []}, "childNode": _approval("B", users=(2,))},
    ])}
    xml, _ = flow_compiler.compile_tree(tree)

    wf = _run(xml, [(["A"], "approve")], {"reason": "紧急", "tags": ["加急"]})
    assert bpmn_engine.reached_end(wf) == "end_approved"
    _run(xml, [(["B"], "approve")], {"reason": "普通", "tags": ["加急"]})
    _run(xml, [(["B"], "approve")], {"reason": "紧急", "tags": []})
