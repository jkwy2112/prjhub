"""BPMN approval flow tests (SpiffWorkflow engine behind the API)."""
from tests.conftest import login_as, make_user


def _create_users(client, admin_headers):
    l1 = make_user(client, "ap_l1", name="一级审批人")
    l2 = make_user(client, "ap_l2", name="二级审批人")
    cs = [make_user(client, f"ap_cs{i}", name=f"会签人{i}") for i in range(3)]
    return l1, l2, cs


def _start(client, headers, title="采购申请", amount=100, countersigners=None, approver_l1=None,
           approver_l2=None):
    variables = {
        "amount": amount,
        "approver_l1": approver_l1["id"],
        "approver_l2": approver_l2["id"],
        "countersigners": [u["id"] for u in (countersigners or [])],
        "cs_total": len(countersigners or []),
        "cs_pass": 2 if countersigners else 0,
    }
    resp = client.post("/approvals", headers=headers,
                       json={"definition_key": "generic_approval", "title": title,
                             "variables": variables})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_definitions_seeded(client, admin_headers):
    defs = client.get("/approvals/definitions", headers=admin_headers).json()
    assert any(d["key"] == "generic_approval" for d in defs)


def test_multi_level_approval_chain(client, admin_headers):
    l1, l2, _ = _create_users(client, admin_headers)

    ticket = _start(client, admin_headers, amount=100, approver_l1=l1, approver_l2=l2)
    assert ticket["status"] == "running"
    assert len(ticket["tasks"]) == 1
    t1 = ticket["tasks"][0]
    assert t1["node_id"] == "ut_l1"
    assert t1["assignee_id"] == l1["id"]

    # only assignee can act
    resp = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                       json={"action": "approve"})
    # superuser bypass is allowed; but let's use the real assignee for the chain
    assert resp.status_code == 200
    ticket2 = resp.json()
    assert ticket2["status"] == "running"
    t2 = [t for t in ticket2["tasks"] if t["status"] == "pending"]
    assert len(t2) == 1 and t2[0]["node_id"] == "ut_l2"

    final = client.post(f"/approvals/tasks/{t2[0]['id']}/complete", headers=admin_headers,
                        json={"action": "approve"}).json()
    assert final["status"] == "approved"
    assert all(t["status"] != "pending" for t in final["tasks"])


def test_reject_short_circuits(client, admin_headers):
    l1, l2, _ = _create_users(client, admin_headers)
    h1 = login_as(client, "ap_l1")

    ticket = _start(client, admin_headers, amount=500, approver_l1=l1, approver_l2=l2)
    t1 = ticket["tasks"][0]

    done = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                       json={"action": "reject", "comment": "预算不足"}).json()
    assert done["status"] == "rejected"
    assert done["tasks"][0]["action"] == "reject"
    assert done["tasks"][0]["comment"] == "预算不足"
    assert all(t["status"] != "pending" for t in done["tasks"])  # no L2 todo remains


def test_condition_gateway_and_or_sign(client, admin_headers):
    l1, l2, cs = _create_users(client, admin_headers)
    h_cs0 = login_as(client, "ap_cs0")
    h_cs1 = login_as(client, "ap_cs1")

    ticket = _start(client, admin_headers, amount=50000, countersigners=cs,
                    approver_l1=l1, approver_l2=l2)
    # L1 first
    t1 = ticket["tasks"][0]
    ticket2 = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                          json={"action": "approve"}).json()
    pending = [t for t in ticket2["tasks"] if t["status"] == "pending"]
    assert len(pending) == 3, "countersign should create 3 parallel todos"
    assignees = {t["assignee_id"] for t in pending}
    assert assignees == {u["id"] for u in cs}
    assert all(t["node_id"] == "ut_cs" for t in pending)

    # or-sign: 2 of 3 approve -> ticket approved, 3rd auto-cancelled
    by_user = {t["assignee_id"]: t for t in pending}
    r1 = client.post(f"/approvals/tasks/{by_user[cs[0]['id']]['id']}/complete", headers=h_cs0,
                     json={"action": "approve"}).json()
    assert r1["status"] == "running"
    r2 = client.post(f"/approvals/tasks/{by_user[cs[1]['id']]['id']}/complete", headers=h_cs1,
                     json={"action": "approve"}).json()
    assert r2["status"] == "approved"
    statuses = {t["status"] for t in r2["tasks"] if t["node_id"] == "ut_cs"}
    assert statuses == {"completed", "cancelled"}, "remaining instance should be auto-cancelled"


def test_countersign_reject(client, admin_headers):
    l1, l2, cs = _create_users(client, admin_headers)
    h_cs0 = login_as(client, "ap_cs0")
    h_cs1 = login_as(client, "ap_cs1")

    ticket = _start(client, admin_headers, amount=99999, countersigners=cs,
                    approver_l1=l1, approver_l2=l2)
    t1 = ticket["tasks"][0]
    ticket2 = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                          json={"action": "approve"}).json()
    pending = {t["assignee_id"]: t for t in ticket2["tasks"] if t["status"] == "pending"}

    client.post(f"/approvals/tasks/{pending[cs[0]['id']]['id']}/complete", headers=h_cs0,
                json={"action": "approve"})
    final = client.post(f"/approvals/tasks/{pending[cs[1]['id']]['id']}/complete", headers=h_cs1,
                        json={"action": "reject"}).json()
    assert final["status"] == "rejected"


def test_assignee_guard_and_persistence(client, admin_headers):
    l1, l2, _ = _create_users(client, admin_headers)
    stranger = make_user(client, "ap_stranger")
    h_stranger = login_as(client, "ap_stranger")
    h1 = login_as(client, "ap_l1")

    ticket = _start(client, admin_headers, amount=100, approver_l1=l1, approver_l2=l2)
    t1 = ticket["tasks"][0]

    # stranger cannot act
    denied = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h_stranger,
                         json={"action": "approve"})
    assert denied.status_code == 403

    # double complete rejected
    ok = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                     json={"action": "approve"})
    assert ok.status_code == 200
    again = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                        json={"action": "approve"})
    assert again.status_code == 400

    # my-pending for L2
    h2 = login_as(client, "ap_l2")
    pend = client.get("/approvals/my-pending", headers=h2).json()
    assert any(p["ticket"]["id"] == ticket["id"] for p in pend)

    # submitter view + cancel guard (already used approve chain; test cancel on fresh ticket)
    fresh = _start(client, admin_headers, amount=1, approver_l1=l1, approver_l2=l2, title="测试撤回")
    cancelled = client.post(f"/approvals/{fresh['id']}/cancel", headers=admin_headers).json()
    assert cancelled["status"] == "cancelled"
    t_after = client.get(f"/approvals/{fresh['id']}", headers=admin_headers).json()
    assert all(t["status"] != "pending" for t in t_after["tasks"])
