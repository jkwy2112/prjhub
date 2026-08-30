"""Stage-D tests (wflow full-merge): uploads, SELF approver, TO_NODE refuse, NEXT mode, timeout actions."""
from io import BytesIO

from app.db import SessionLocal
from app.models import ApprovalTask, User
from unittest.mock import patch

from tests.conftest import login_as, make_user


def _deploy(client, headers, key, tree, form_items=None):
    resp = client.post("/approvals/definitions/tree", headers=headers,
                       json={"key": key, "name": key, "tree": tree,
                             "form_items": form_items or []})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_upload_file(client, admin_headers):
    resp = client.post("/uploads", headers=admin_headers,
                       files={"file": ("test.png", BytesIO(b"\x89PNG fake"), "image/png")})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["url"].startswith("/uploads/") and body["name"] == "test.png"

    # file is served
    got = client.get(body["url"])
    assert got.status_code == 200 and b"PNG" in got.content

    # bad ext rejected
    bad = client.post("/uploads", headers=admin_headers,
                      files={"file": ("evil.exe", BytesIO(b"x"), "application/x-exe")})
    assert bad.status_code == 400


def test_approver_self_and_nobody_to_user(client, admin_headers):
    boss = make_user(client, "d_boss", name="主管")
    fallback = make_user(client, "d_fallback", name="转交对象")
    ghost = make_user(client, "d_ghost", name="离职者")

    # 1) SELF: submitter is the approver
    tree_self = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "发起人自审",
        "props": {"assigneeType": "self", "users": [], "mode": "any"}, "childNode": None}}
    _deploy(client, admin_headers, "d_self", tree_self)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_self", "title": "自审"}).json()
    assert ticket["tasks"][0]["assignee_id"] == ticket["submitted_by"] == 1

    # 2) nobody=to_user: ghost-only approvers bounce to the configured fallback user
    tree_bounce = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "空节点",
        "props": {"assigneeType": "users", "users": [ghost["id"]], "mode": "any",
                  "nobody": {"handler": "to_user", "users": [fallback["id"]]}},
        "childNode": None}}
    _deploy(client, admin_headers, "d_bounce", tree_bounce)

    from app.db import SessionLocal
    from app.models import ApprovalTask, User

    db = SessionLocal()
    try:
        db.query(User).filter(User.id == ghost["id"]).update({"is_active": False})
        db.commit()
    finally:
        db.close()

    ticket2 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_bounce", "title": "转交"}).json()
    assert ticket2["tasks"][0]["assignee_id"] == fallback["id"]

    # legacy boss node still works with direct assignee
    tree_ok = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "主管",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"}, "childNode": None}}
    _deploy(client, admin_headers, "d_ok", tree_ok)
    ticket3 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_ok", "title": "正常"}).json()
    assert ticket3["tasks"][0]["assignee_id"] == boss["id"]


def test_refuse_to_node(client, admin_headers):
    l1 = make_user(client, "tn_l1", name="一级")
    l2 = make_user(client, "tn_l2", name="二级")
    l3 = make_user(client, "tn_l3", name="三级")

    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "一级审批",
        "props": {"assigneeType": "users", "users": [l1["id"]], "mode": "any"},
        "childNode": {
            "type": "APPROVAL", "name": "二级审批",
            "props": {"assigneeType": "users", "users": [l2["id"]], "mode": "any"},
            "childNode": {
                "type": "APPROVAL", "name": "三级审批",
                "props": {"assigneeType": "users", "users": [l3["id"]], "mode": "any",
                          "refuse": "TO_NODE", "refuseTarget": "ut_ap1"},
                "childNode": None,
            }}}}
    _deploy(client, admin_headers, "d_tn", tree)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_tn", "title": "驳回到指定节点"}).json()
    h1, h2, h3 = login_as(client, "tn_l1"), login_as(client, "tn_l2"), login_as(client, "tn_l3")

    t1 = [t for t in ticket["tasks"] if t["status"] == "pending"][0]
    r1 = client.post(f"/approvals/tasks/{t1['id']}/complete", headers=h1,
                     json={"action": "approve"}).json()
    t2 = [t for t in r1["tasks"] if t["status"] == "pending"][0]
    r2 = client.post(f"/approvals/tasks/{t2['id']}/complete", headers=h2,
                     json={"action": "approve"}).json()
    t3 = [t for t in r2["tasks"] if t["status"] == "pending"][0]
    assert t3["node_name"] == "三级审批"

    # L3 refuses back to L1 (designated node, two levels down)
    back = client.post(f"/approvals/tasks/{t3['id']}/complete", headers=h3,
                       json={"action": "reject"}).json()
    assert back["status"] == "running"
    pending = [t for t in back["tasks"] if t["status"] == "pending"]
    assert pending and pending[0]["node_name"] == "一级审批"

    # self-ref to own node rejected at compile time
    bad_tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "自指",
        "props": {"assigneeType": "users", "users": [1], "mode": "any",
                  "refuse": "TO_NODE", "refuseTarget": "ut_ap1"}, "childNode": None}}
    resp = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "d_tn_bad", "name": "x", "tree": bad_tree})
    assert resp.status_code == 400 and "不能驳回到自身" in resp.json()["detail"]


def test_next_sequential_countersign(client, admin_headers):
    u = [make_user(client, f"nx_{i}", name=f"顺序会签{i}") for i in range(2)]
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "顺序审批",
        "props": {"assigneeType": "users", "users": [x["id"] for x in u],
                  "mode": "next"}, "childNode": None}}
    _deploy(client, admin_headers, "d_next", tree)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_next", "title": "顺序会签"}).json()

    # sequential mode: exactly ONE instance ready at a time, in order
    ready = [t for t in ticket["tasks"] if t["status"] == "pending"]
    assert len(ready) == 1
    h0 = login_as(client, f"nx_0")
    done1 = client.post(f"/approvals/tasks/{ready[0]['id']}/complete", headers=h0,
                        json={"action": "approve"}).json()
    ready2 = [t for t in done1["tasks"] if t["status"] == "pending"]
    assert len(ready2) == 1
    h1 = login_as(client, "nx_1")
    done2 = client.post(f"/approvals/tasks/{ready2[0]['id']}/complete", headers=h1,
                        json={"action": "approve"}).json()
    assert done2["status"] == "approved"


def test_timeout_auto_pass(client, admin_headers):
    from datetime import timedelta

    from app.models import utcnow
    from app.services import reminder as reminder_mod

    slow = make_user(client, "to_slow", name="超时主管")
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "限时",
        "props": {"assigneeType": "users", "users": [slow["id"]], "mode": "any",
                  "timeout": {"enabled": True, "unit": "H", "value": 1, "handler": "PASS"}},
        "childNode": None}}
    _deploy(client, admin_headers, "d_to", tree)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_to", "title": "超时自动通过"}).json()

    db = SessionLocal()
    try:
        row = (db.query(ApprovalTask)
               .filter(ApprovalTask.ticket_id == ticket["id"]).first())
        row.due_at = utcnow() - timedelta(minutes=1)
        db.commit()

        count = reminder_mod.remind_overdue()
        assert count >= 1
        t = client.get(f"/approvals/{ticket['id']}", headers=admin_headers).json()
        assert t["status"] == "approved", "timeout PASS should auto-approve"
        auto = [x for x in t["tasks"] if x["id"] == row.id][0]
        assert auto["action"] == "approve" and "超时" in auto["comment"]
    finally:
        db.close()


def test_upload_used_in_form_roundtrip(client, admin_headers):
    up = client.post("/uploads", headers=admin_headers,
                     files={"file": ("a.jpg", BytesIO(b"jpg"), "image/jpeg")}).json()
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "审图",
        "props": {"assigneeType": "users", "users": [1], "mode": "any"}, "childNode": None}}
    resp = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "d_img", "name": "图片审批", "tree": tree,
                             "form_items": [{"id": "f_img", "name": "ImageUpload", "title": "现场照片",
                                             "valueType": "Array", "props": {"required": True}}]})
    assert resp.status_code == 201

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "d_img", "title": "图单",
        "variables": {"f_img": [up["url"]]}}).json()
    assert ticket["form_values"]["f_img"] == [up["url"]]
