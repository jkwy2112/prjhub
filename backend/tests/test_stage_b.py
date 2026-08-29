"""Stage-B features: CC nodes, nobody policy, refuse TO_BEFORE."""
from tests.conftest import make_user


def _deploy(client, headers, tree):
    resp = client.post("/approvals/definitions/tree", headers=headers,
                       json={"key": f"stage_b_{abs(hash(str(tree))) % 99999}", "name": "B", "tree": tree})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_cc_node_notifies_and_never_blocks(client, admin_headers):
    boss = make_user(client, "b_boss", name="主管")
    watcher = make_user(client, "b_watcher", name="抄送人")

    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "主管审批",
        "props": {"assigneeType": "runtime", "users": [], "mode": "any"},
        "childNode": {
            "type": "CC", "name": "抄送财务",
            "props": {"assigneeType": "users", "users": [watcher["id"]]},
            "childNode": {
                "type": "APPROVAL", "name": "复核",
                "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                "childNode": None,
            },
        },
    }}
    definition = _deploy(client, admin_headers, tree)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": definition["key"], "title": "带抄送的审批",
        "variables": {"approver_ut_ap1": [admin_headers and 1]},
    }).json()

    # CC sits AFTER the boss approval: no cc record yet, only the boss todo is pending
    pendings = [t for t in ticket["tasks"] if t["status"] == "pending"]
    assert [t["node_name"] for t in pendings] == ["主管审批"]
    assert not [t for t in ticket["tasks"] if t["action"] == "cc"]

    done = client.post(f"/approvals/tasks/{pendings[0]['id']}/complete", headers=admin_headers,
                       json={"action": "approve"}).json()
    # boss approved -> CC auto-completed instantly (record for watcher) -> 复核 pending
    cc_rows = [t for t in done["tasks"] if t["action"] == "cc"]
    assert len(cc_rows) == 1 and cc_rows[0]["assignee_id"] == watcher["id"]
    names = [t["node_name"] for t in done["tasks"] if t["status"] == "pending"]
    assert names == ["复核"]
    fin = client.post(f"/approvals/tasks/{[t['id'] for t in done['tasks'] if t['status']=='pending'][0]}/complete",
                      headers=admin_headers, json={"action": "approve"}).json()
    assert fin["status"] == "approved"


def test_nobody_auto_pass(client, admin_headers):
    boss = make_user(client, "nb_boss", name="主管")
    ghost = make_user(client, "nb_ghost", name="将离职")

    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "空审批节点",
        "props": {"assigneeType": "users", "users": [ghost["id"]], "mode": "any", "nobody": "auto_pass"},
        "childNode": {
            "type": "APPROVAL", "name": "主管",
            "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
            "childNode": None,
        },
    }}
    definition = _deploy(client, admin_headers, tree)

    # disable the ghost user -> their node has no valid assignees
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        db.query(User).filter(User.id == ghost["id"]).update({"is_active": False})
        db.commit()
    finally:
        db.close()

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": definition["key"], "title": "空审批单"}).json()
    auto = [t for t in ticket["tasks"] if t["comment"] == "审批人为空, 自动处理"]
    assert len(auto) == 1 and auto[0]["action"] == "approve"
    pendings = [t for t in ticket["tasks"] if t["status"] == "pending"]
    assert [t["node_name"] for t in pendings] == ["主管"]


def test_refuse_to_before_returns_for_re_approval(client, admin_headers):
    boss = make_user(client, "rb_boss", name="一级主管")
    boss2 = make_user(client, "rb_boss2", name="二级主管")

    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "一级审批",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
        "childNode": {
            "type": "APPROVAL", "name": "二级审批",
            "props": {"assigneeType": "users", "users": [boss2["id"]], "mode": "any",
                      "refuse": "TO_BEFORE"},
            "childNode": None,
        },
    }}
    definition = _deploy(client, admin_headers, tree)
    from tests.conftest import login_as
    h1 = login_as(client, "rb_boss")
    h2 = login_as(client, "rb_boss2")

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": definition["key"], "title": "退回重审"}).json()

    # L1 approve
    t1 = [t for t in ticket["tasks"] if t["status"] == "pending"][0]
    after = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                        json={"action": "approve"}).json()
    assert after["status"] == "running"
    t2 = [t for t in after["tasks"] if t["status"] == "pending"][0]
    assert t2["node_name"] == "二级审批"

    # L2 reject with TO_BEFORE -> back to L1 (not terminated)
    back = client.post(f"/approvals/tasks/{t2['id']}/complete", headers=h2,
                       json={"action": "reject", "comment": "材料不全"}).json()
    assert back["status"] == "running", "TO_BEFORE must not terminate the ticket"
    pending = [t for t in back["tasks"] if t["status"] == "pending"]
    assert pending and pending[0]["node_name"] == "一级审批"

    # L1 approves again -> L2 approves -> approved
    again = client.post(f"/approvals/tasks/{pending[0]['id']}/complete", headers=h1,
                        json={"action": "approve"}).json()
    t2b = [t for t in again["tasks"] if t["status"] == "pending"][0]
    final = client.post(f"/approvals/tasks/{t2b['id']}/complete", headers=h2,
                        json={"action": "approve"}).json()
    assert final["status"] == "approved"
