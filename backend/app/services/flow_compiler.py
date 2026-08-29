"""Compile a WFlow-style nested process tree into BPMN 2.0 XML (Python-expression conditions).

Tree model (designer JSON, single source of truth):
  ROOT -> childNode chain
  APPROVAL    props: assigneeType 'users'|'runtime', users[], mode 'any'|'all'|'count', count
  CONDITIONS  branches: [{props.groups, childNode}], group childNode = post-merge chain
  CONCURRENTS branches: [{childNode}], same merge semantics

Compile strategy: recursively map each tree node/branch-group to an element pair
(entry_id, exit_id), connecting edges afterwards. Default gateway routing is derived
automatically at serialization time (the sole unconditional outgoing edge of an
exclusive gateway becomes its default).
"""
from typing import Optional
from xml.sax.saxutils import escape, quoteattr

END_APPROVED = "end_approved"
END_REJECTED = "end_rejected"


class FlowCompileError(Exception):
    pass


def _num(v, ctx=""):
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return float(v)
        except (TypeError, ValueError):
            raise FlowCompileError(f"{ctx}条件值 {v!r} 不是数字")


def _str(v):
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _cond_expression(cond: dict) -> str:
    field = str(cond.get("field", "")).strip()
    if not field:
        raise FlowCompileError("条件字段不能为空")
    if not field.replace("_", "").isalnum():
        raise FlowCompileError(f"条件字段 {field} 不合法 (仅限字母数字下划线)")
    vtype = cond.get("valueType") or "Number"
    op = cond.get("compare", "==")
    value = cond.get("value") or []

    if vtype == "Number":
        if op == "between":
            if len(value) != 2:
                raise FlowCompileError(f"条件「{field}」的区间比较需要 [下限, 上限] 两个值")
            return f"({_num(value[0])} <= {field} <= {_num(value[1])})"
        if op not in (">", ">=", "<", "<=", "=="):
            raise FlowCompileError(f"数字字段不支持比较符 {op}")
        if not value:
            raise FlowCompileError(f"条件「{field}」缺少比较值")
        return f"{field} {op} {_num(value[0], field)}"
    if vtype == "Array":
        if op != "in":
            raise FlowCompileError("多选字段仅支持「属于」比较")
        if not value:
            raise FlowCompileError(f"条件「{field}」的枚举值不能为空")
        options = ", ".join(_str(v) for v in value)
        return f"len(set([{options}]) & set({field} or [])) > 0"
    # String / Date
    if op == "in":
        if not value:
            raise FlowCompileError(f"条件「{field}」的枚举值不能为空")
        options = ", ".join(_str(v) for v in value)
        return f"{field} in [{options}]"
    if op in ("==", "!="):
        if not value:
            raise FlowCompileError(f"条件「{field}」缺少比较值")
        return f"{field} {op} {_str(value[0])}"
    raise FlowCompileError(f"文本字段不支持比较符 {op} (可用 = / 属于)")


def _group_expression(group: dict) -> str:
    conds = [_cond_expression(c) for c in group.get("conditions", [])]
    if not conds:
        raise FlowCompileError("条件组内至少需要一个条件")
    joiner = " and " if group.get("groupType", "AND") == "AND" else " or "
    return f"({joiner.join(conds)})" if len(conds) > 1 else conds[0]


def _branch_expression(props: Optional[dict]) -> Optional[str]:
    groups = [g for g in (props or {}).get("groups", []) if g.get("conditions")]
    if not groups:
        return None  # default branch
    exprs = [_group_expression(g) for g in groups]
    joiner = " and " if (props or {}).get("groupsType", "AND") == "AND" else " or "
    return joiner.join(exprs)


class _Graph:
    def __init__(self):
        self.elements: "dict[str, dict]" = {}
        self.edges: "list[dict]" = []
        self._seq = 0
        self._ap = 0
        self._cc = 0
        self._gw = 0

    def element(self, eid, tag, **attrs):
        self.elements[eid] = {"tag": tag, "attrs": attrs, "mi": None}
        return eid

    def edge(self, src, dst, condition=None, name=""):
        self._seq += 1
        self.edges.append({"id": f"sf{self._seq}", "src": src, "dst": dst,
                           "condition": condition, "name": name})
        return f"sf{self._seq}"

    def ap_id(self):
        self._ap += 1
        return f"ut_ap{self._ap}"

    def cc_id(self):
        self._cc += 1
        return f"ut_cc{self._cc}"

    def gw_id(self, prefix):
        self._gw += 1
        return f"{prefix}{self._gw}"


def compile_tree(tree: dict, process_id: str = "Designed_Approval") -> "tuple[str, dict]":
    """Validate + compile a designer tree. Returns (bpmn_xml, node_meta)."""
    if not isinstance(tree, dict) or not tree.get("childNode"):
        raise FlowCompileError("流程至少需要一个审批节点")

    g = _Graph()
    meta: dict = {}
    g.element("start", "bpmn:startEvent")
    g.element(END_APPROVED, "bpmn:endEvent", name="审批通过")
    g.element(END_REJECTED, "bpmn:endEvent", name="审批驳回", terminate=True)

    entry, exit_, _ = _compile_chain(g, tree["childNode"], meta, depth=0)
    g.edge("start", entry)
    g.edge(exit_, END_APPROVED)

    xml = _serialize(g, process_id)
    return xml, meta


def _compile_chain(g: _Graph, node: Optional[dict], meta: dict, depth: int,
                   prev_approval: Optional[str] = None):
    """Returns (entry_id, exit_id, last_approval_id); last follows depth-first order."""
    if depth > 20:
        raise FlowCompileError("流程嵌套层级过深 (最多 20 层)")
    if not node:
        return None, None, prev_approval

    e1, x1, own = _compile_single(g, node, meta, depth, prev_approval)
    child = node.get("childNode")
    e2, x2, last = _compile_chain(g, child, meta, depth + 1, own)
    if e2 is not None:
        g.edge(x1, e2)
        return e1, x2, last
    return e1, x1, own


def _compile_single(g: _Graph, node: dict, meta: dict, depth: int,
                    prev_approval: Optional[str]):
    ntype = node.get("type")
    if ntype == "APPROVAL":
        return _compile_approval(g, node, meta, prev_approval)
    if ntype == "CC":
        return _compile_cc(g, node, meta, prev_approval)
    if ntype == "CONDITIONS":
        return _compile_group(g, node, meta, depth, parallel=False, prev_approval=prev_approval)
    if ntype == "CONCURRENTS":
        return _compile_group(g, node, meta, depth, parallel=True, prev_approval=prev_approval)
    raise FlowCompileError(f"不支持的节点类型 {ntype}")


def _approval_meta(g: _Graph, node: dict, meta: dict) -> str:
    """Create the user task element (with multi-instance when needed), return its id."""
    tid = g.ap_id()
    props = node.get("props") or {}
    name = str(node.get("name") or "审批").strip() or "审批"
    assignee_type = props.get("assigneeType", "users")
    users = props.get("users") or []
    mode = props.get("mode", "any")
    count = int(props.get("count") or 0)
    nobody = props.get("nobody", "to_admin")

    if assignee_type not in ("users", "runtime"):
        raise FlowCompileError(f"审批节点「{name}」审批人类型不合法")
    if assignee_type == "users" and not users:
        raise FlowCompileError(f"审批节点「{name}」未指定审批成员")
    if mode not in ("any", "all", "count"):
        raise FlowCompileError(f"审批节点「{name}」签核模式不合法")
    if mode == "count" and count < 1:
        raise FlowCompileError(f"审批节点「{name}」票签数需 ≥ 1")
    if nobody not in ("to_admin", "auto_pass", "auto_reject"):
        raise FlowCompileError(f"审批节点「{name}」审批人为空策略不合法")

    multi = len(users) > 1 or assignee_type == "runtime"
    if multi:
        if assignee_type == "users":
            cardinality = str(len(users))
            pass_n = 1 if mode == "any" else (len(users) if mode == "all" else min(count, len(users)))
            completion = f"completed_count >= {pass_n} or rejected"
        else:
            cardinality = f"assignee_total_{tid}"
            if mode == "any":
                completion = "completed_count >= 1 or rejected"
            elif mode == "all":
                completion = f"completed_count >= assignee_total_{tid} or rejected"
            else:
                completion = f"completed_count >= pass_{tid} or rejected"
        g.element(tid, "bpmn:userTask", name=name)
        g.elements[tid]["mi"] = {"cardinality": cardinality, "completion": completion}
    else:
        g.element(tid, "bpmn:userTask", name=name)

    meta[tid] = {"type": "APPROVAL", "name": name, "assigneeType": assignee_type,
                 "users": users, "mode": mode, "count": count, "nobody": nobody}
    node["bpmnId"] = tid  # write back so the launch form can build approver_<tid> variables
    return tid


def _compile_approval(g: _Graph, node: dict, meta: dict, prev_approval: Optional[str]):
    """approval -> reject gateway. Entry = task, exit = gateway (continue edge is unconditional).

    refuse rule: TO_END -> terminate end (default); TO_BEFORE -> edge back to the previous
    approval task (depth-first order) for re-approval; falls back to END when none exists.
    """
    tid = _approval_meta(g, node, meta)
    gw = g.gw_id("gw_rej")
    g.element(gw, "bpmn:exclusiveGateway", gatewayDirection="Diverging")
    g.edge(tid, gw)
    refuse = (node.get("props") or {}).get("refuse", "TO_END")
    if refuse not in ("TO_END", "TO_BEFORE"):
        raise FlowCompileError(f"审批节点「{meta[tid]['name']}」驳回规则不合法")
    if refuse == "TO_BEFORE" and prev_approval:
        g.edge(gw, prev_approval, condition="rejected", name="驳回到上一节点")
        meta[tid]["refuse"] = "TO_BEFORE"
        meta[tid]["returnTo"] = prev_approval
    else:
        g.edge(gw, END_REJECTED, condition="rejected", name="驳回")
    return tid, gw, tid


def _compile_cc(g: _Graph, node: dict, meta: dict, prev_approval: Optional[str]):
    """CC node -> user task auto-completed by the service layer (never blocks the flow).

    Returns the incoming prev_approval unchanged so TO_BEFORE chains pass through CC.
    """
    tid = g.cc_id()
    props = node.get("props") or {}
    name = str(node.get("name") or "抄送人").strip() or "抄送人"
    assignee_type = props.get("assigneeType", "users")
    users = props.get("users") or []
    if assignee_type not in ("users", "runtime"):
        raise FlowCompileError(f"抄送节点「{name}」抄送人类型不合法")
    if assignee_type == "users" and not users:
        raise FlowCompileError(f"抄送节点「{name}」未指定抄送成员")
    g.element(tid, "bpmn:userTask", name=name)
    meta[tid] = {"type": "CC", "name": name, "assigneeType": assignee_type, "users": users}
    node["bpmnId"] = tid
    return tid, tid, prev_approval


def _compile_group(g: _Graph, node: dict, meta: dict, depth: int, parallel: bool,
                   prev_approval: Optional[str]):
    tag = "bpmn:parallelGateway" if parallel else "bpmn:exclusiveGateway"
    label = "并行分支" if parallel else "条件分支"
    branches = node.get("branches") or []
    if len(branches) < 2:
        raise FlowCompileError(f"{label}至少需要 2 个分支")

    fork = g.gw_id("gw_pf" if parallel else "gw_cf")
    join = g.gw_id("gw_pj" if parallel else "gw_cj")
    g.element(fork, tag, gatewayDirection="Diverging")
    g.element(join, tag, gatewayDirection="Converging")

    expressions = [_branch_expression(b.get("props")) for b in branches] if not parallel else [None] * len(branches)

    last_in_branches = prev_approval
    for i, branch in enumerate(branches):
        chain = _compile_chain(g, branch.get("childNode"), meta, depth + 1, prev_approval)
        bname = str(branch.get("name") or f"分支{i + 1}")
        if chain[0] is None:
            g.edge(fork, join, name=bname)
            continue
        if not parallel and expressions[i] is not None:
            g.edge(fork, chain[0], condition=expressions[i], name=bname)
        else:
            g.edge(fork, chain[0], name=bname)
        g.edge(chain[1], join)
        last_in_branches = chain[2] or last_in_branches

    # NOTE: the group's childNode (post-merge chain) is connected by _compile_chain,
    # which receives last_in_branches as `own` so nested approvals chain correctly.
    return fork, join, last_in_branches


def _serialize(g: _Graph, process_id: str) -> str:
    incoming: "dict[str, list]" = {}
    outgoing: "dict[str, list]" = {}
    for e in g.edges:
        if not e["dst"] or not e["src"]:
            raise FlowCompileError("内部编译错误: 存在未连接的流转")
        outgoing.setdefault(e["src"], []).append(e["id"])
        incoming.setdefault(e["dst"], []).append(e["id"])

    # exclusive gateways with conditional outgoings: their unconditional outgoing is the default
    defaults: "dict[str, str]" = {}
    for eid, el in g.elements.items():
        if el["tag"] != "bpmn:exclusiveGateway":
            continue
        outs = [e for e in g.edges if e["src"] == eid]
        if any(e["condition"] for e in outs):
            plain = [e for e in outs if not e["condition"]]
            if plain:
                defaults[eid] = plain[0]["id"]

    parts = []
    for eid, el in g.elements.items():
        tag = el["tag"]
        frag = f'<{tag} id="{eid}"'
        for k, v in el["attrs"].items():
            frag += f" {k}={quoteattr(str(v))}"
        if eid in defaults:
            frag += f' default="{defaults[eid]}"'
        frag += ">"
        for ref in incoming.get(eid, []):
            frag += f"<bpmn:incoming>{ref}</bpmn:incoming>"
        for ref in outgoing.get(eid, []):
            frag += f"<bpmn:outgoing>{ref}</bpmn:outgoing>"
        if el.get("mi"):
            frag += (
                '<bpmn:multiInstanceLoopCharacteristics isSequential="false">'
                f"<bpmn:loopCardinality>{escape(el['mi']['cardinality'])}</bpmn:loopCardinality>"
                f"<bpmn:completionCondition>{escape(el['mi']['completion'])}</bpmn:completionCondition>"
                "</bpmn:multiInstanceLoopCharacteristics>"
            )
        if el["attrs"].get("terminate"):
            frag += "<bpmn:terminateEventDefinition/>"
        frag += f"</{tag}>"
        parts.append(frag)

    for e in g.edges:
        frag = f'<bpmn:sequenceFlow id="{e["id"]}" sourceRef="{e["src"]}" targetRef="{e["dst"]}"'
        if e.get("name"):
            frag += f' name={quoteattr(e["name"])}'
        if e.get("condition"):
            frag += (
                '><bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">'
                f"{escape(e['condition'])}</bpmn:conditionExpression></bpmn:sequenceFlow>"
            )
        else:
            frag += "/>"
        parts.append(frag)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'id="Defs_{process_id}" targetNamespace="http://prjhub.local/bpmn">'
        f'<bpmn:process id="{process_id}" isExecutable="true">{"".join(parts)}</bpmn:process>'
        "</bpmn:definitions>"
    )
