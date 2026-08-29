"""End-to-end tests for visually designed flows (tree -> BPMN -> tickets)."""
from tests.conftest import login_as, make_user


def _deploy_custom_flow(client, headers, cs_users, fin_user):
    tree = {
        "type": "ROOT",
        "childNode": {
            "type": "APPROVAL", "name": "主管审批",
            "props": {"assigneeType": "runtime", "users": [], "mode": "any"},
            "childNode": {
                "type": "CONDITIONS",
                "branches": [
                    {"type": "CONDITION", "name": "大额",
                     "props": {"groupsType": "AND", "groups": [
                         {"groupType": "AND", "conditions": [
                             {"field": "amount", "compare": ">", "value": [1000]}]}]},
                     "childNode": {
                         "type": "APPROVAL", "name": "会签",
                         "props": {"assigneeType": "users", "users": cs_users,
                                   "mode": "count", "count": 2}}},
                    {"type": "CONDITION", "name": "默认", "props": {"groups": []},
                     "childNode": {
                         "type": "APPROVAL", "name": "财务",
                         "props": {"assigneeType": "users", "users": [fin_user], "mode": "any"}}},
                ],
                "childNode": None,
            },
        },
    }
    resp = client.post("/approvals/definitions/tree", headers=headers,
                       json={"key": "custom_expense", "name": "自定义报销", "tree": tree})
    assert resp.status_code == 201, resp.text
    return resp.json(), tree


def _setup_users(client):
    boss = make_user(client, "ds_boss", name="主管")
    fin = make_user(client, "ds_fin", name="财务")
    cs = [make_user(client, f"ds_cs{i}", name=f"会签人{i}") for i in range(3)]
    return boss, fin, cs


def test_deploy_tree_and_definition_list(client, admin_headers):
    boss, fin, cs = _setup_users(client)
    definition, tree = _deploy_custom_flow(client, admin_headers, [u["id"] for u in cs], fin["id"])
    assert definition["version"] == 1

    defs = client.get("/approvals/definitions", headers=admin_headers).json()
    mine = [d for d in defs if d["key"] == "custom_expense"][0]
    assert mine["has_tree"] is True

    # tree roundtrip for designer (bpmnId written back by compiler)
    got = client.get(f"/approvals/definitions/{definition['id']}/tree", headers=admin_headers).json()
    assert got["tree"]["childNode"]["name"] == "主管审批"
    assert got["tree"]["childNode"]["bpmnId"] == "ut_ap1"


def test_deploy_tree_rejects_unknown_members(client, admin_headers):
    bad = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "幽灵审批",
        "props": {"assigneeType": "users", "users": [99999], "mode": "any"}}}
    resp = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "ghost_flow", "name": "x", "tree": bad})
    assert resp.status_code == 400
    assert "不存在" in resp.json()["detail"]


def test_designed_flow_full_lifecycle(client, admin_headers):
    boss, fin, cs = _setup_users(client)
    definition, tree = _deploy_custom_flow(client, admin_headers, [u["id"] for u in cs], fin["id"])
    h_fin = login_as(client, "ds_fin")

    # small amount: runtime boss -> fixed finance
    resp = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "custom_expense",
        "title": "小额报销",
        "variables": {"amount": 500, "approver_ut_ap1": [boss["id"]]},
    })
    assert resp.status_code == 201, resp.text
    ticket = resp.json()
    assert ticket["definition_key"] == "custom_expense"
    t1 = ticket["tasks"][0]
    assert t1["node_name"] == "主管审批" and t1["assignee_id"] == boss["id"]

    after = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                        json={"action": "approve"}).json()
    fin_task = [t for t in after["tasks"] if t["status"] == "pending"][0]
    assert fin_task["node_name"] == "财务" and fin_task["assignee_id"] == fin["id"]
    final = client.post(f"/approvals/tasks/{fin_task['id']}/complete", headers=h_fin,
                        json={"action": "approve"}).json()
    assert final["status"] == "approved"


def test_designed_flow_countersign_fixed_members(client, admin_headers):
    boss, fin, cs = _setup_users(client)
    definition, tree = _deploy_custom_flow(client, admin_headers, [u["id"] for u in cs], fin["id"])
    h_cs = [login_as(client, f"ds_cs{i}") for i in range(3)]

    resp = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "custom_expense",
        "title": "大额报销",
        "variables": {"amount": 8000, "approver_ut_ap1": [boss["id"]]},
    })
    ticket = resp.json()
    t1 = ticket["tasks"][0]
    after = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                        json={"action": "approve"}).json()
    cs_tasks = [t for t in after["tasks"] if t["status"] == "pending"]
    assert len(cs_tasks) == 3
    assert {t["assignee_id"] for t in cs_tasks} == {u["id"] for u in cs}

    # 2 of 3 approve (mode=count 2) -> approved, third auto-cancelled
    by_user = {t["assignee_id"]: t for t in cs_tasks}
    r1 = client.post(f"/approvals/tasks/{by_user[cs[0]['id']]['id']}/complete", headers=h_cs[0],
                     json={"action": "approve"}).json()
    assert r1["status"] == "running"
    r2 = client.post(f"/approvals/tasks/{by_user[cs[1]['id']]['id']}/complete", headers=h_cs[1],
                     json={"action": "approve"}).json()
    assert r2["status"] == "approved"
    leftover = [t for t in r2["tasks"] if t["node_id"] == "ut_ap2" and t["status"] == "cancelled"]
    assert any(t["assignee_id"] == cs[2]["id"] for t in leftover)


def test_designed_flow_validation_error(client, admin_headers):
    bad = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "无人审批",
        "props": {"assigneeType": "users", "users": [], "mode": "any"}}}
    resp = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "bad_flow", "name": "x", "tree": bad})
    assert resp.status_code == 400
    assert "未指定审批成员" in resp.json()["detail"]


def test_designed_flow_missing_runtime_assignee_rejected(client, admin_headers):
    boss, fin, cs = _setup_users(client)
    _deploy_custom_flow(client, admin_headers, [u["id"] for u in cs], fin["id"])
    resp = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "custom_expense",
        "title": "缺审批人",
        "variables": {"amount": 100},
    })
    assert resp.status_code == 400
    assert "approver_ut_ap1" in resp.json()["detail"]
