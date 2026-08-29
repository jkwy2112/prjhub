"""Parallel multi-branch approval tests (parallel gateway fork/join)."""
from tests.conftest import login_as, make_user


def _setup(client):
    l1 = make_user(client, "pb_l1", name="一级审批人")
    fin = make_user(client, "pb_fin", name="财务审批人")
    tech = make_user(client, "pb_tech", name="技术评审人")
    return l1, fin, tech


def _start(client, headers, l1, fin, tech, title="并行审批单"):
    resp = client.post("/approvals", headers=headers, json={
        "definition_key": "parallel_approval",
        "title": title,
        "variables": {
            "approver_l1": l1["id"],
            "approver_fin": fin["id"],
            "approver_tech": tech["id"],
        },
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_parallel_branches_run_simultaneously(client, admin_headers):
    l1, fin, tech = _setup(client)
    h_fin = login_as(client, "pb_fin")

    ticket = _start(client, admin_headers, l1, fin, tech)

    # L1 approve -> fork activates BOTH branches at the same time
    t1 = ticket["tasks"][0]
    after_l1 = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                           json={"action": "approve"}).json()
    pending = {t["node_id"]: t for t in after_l1["tasks"] if t["status"] == "pending"}
    assert set(pending) == {"ut_fin", "ut_tech"}, "both branches must be pending in parallel"
    assert pending["ut_fin"]["assignee_id"] == fin["id"]
    assert pending["ut_tech"]["assignee_id"] == tech["id"]

    # finish only finance branch -> join waits for tech
    half = client.post(f"/approvals/tasks/{pending['ut_fin']['id']}/complete", headers=h_fin,
                       json={"action": "approve"}).json()
    assert half["status"] == "running"
    still = [t for t in half["tasks"] if t["status"] == "pending"]
    assert [t["node_id"] for t in still] == ["ut_tech"]

    # finish tech branch -> join releases, ticket approved
    final = client.post(f"/approvals/tasks/{still[0]['id']}/complete", headers=admin_headers,
                       json={"action": "approve"}).json()
    assert final["status"] == "approved"


def test_parallel_branch_reject_short_circuits(client, admin_headers):
    l1, fin, tech = _setup(client)
    h_fin = login_as(client, "pb_fin")

    ticket = _start(client, admin_headers, l1, fin, tech)
    t1 = ticket["tasks"][0]
    after_l1 = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=admin_headers,
                           json={"action": "approve"}).json()
    pending = {t["node_id"]: t for t in after_l1["tasks"] if t["status"] == "pending"}

    # finance rejects -> ticket rejected, tech branch todo auto-cancelled
    final = client.post(f"/approvals/tasks/{pending['ut_fin']['id']}/complete", headers=h_fin,
                        json={"action": "reject", "comment": "预算超支"}).json()
    assert final["status"] == "rejected"
    tech_row = [t for t in final["tasks"] if t["node_id"] == "ut_tech"][0]
    assert tech_row["status"] == "cancelled"
    assert all(t["status"] != "pending" for t in final["tasks"])


def test_parallel_first_level_reject(client, admin_headers):
    l1, fin, tech = _setup(client)
    h1 = login_as(client, "pb_l1")

    ticket = _start(client, admin_headers, l1, fin, tech, title="一级即驳回")
    t1 = ticket["tasks"][0]
    final = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                        json={"action": "reject"}).json()
    assert final["status"] == "rejected"
    assert len(final["tasks"]) == 1  # branches never activated
