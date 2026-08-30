"""Stage-C features: form-field approvers, trigger webhooks, timeout reminders, form perms."""
from unittest.mock import patch

from app.db import SessionLocal
from app.models import ApprovalTask, User
from tests.conftest import login_as, make_user


def _deploy(client, headers, tree, form_items, key):
    resp = client.post("/approvals/definitions/tree", headers=headers,
                       json={"key": key, "name": key, "tree": tree, "form_items": form_items})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_form_field_approver(client, admin_headers):
    contact = make_user(client, "c_contact", name="表单联系人")
    boss = make_user(client, "c_boss", name="兜底主管")

    form = [{"id": "f_contact", "name": "UserPicker", "title": "对接人", "valueType": "User",
             "props": {"required": True}}]
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "对接人确认",
        "props": {"assigneeType": "form", "formField": "f_contact", "users": [], "mode": "any"},
        "childNode": {
            "type": "APPROVAL", "name": "主管",
            "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
            "childNode": None,
        }}}
    _deploy(client, admin_headers, tree, form, "stage_c_form")

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "stage_c_form", "title": "表单联系人审批",
        "variables": {"f_contact": contact["id"]},
    }).json()
    first = ticket["tasks"][0]
    assert first["node_name"] == "对接人确认" and first["assignee_id"] == contact["id"]

    h_contact = login_as(client, "c_contact")
    final = client.post(f"/approvals/tasks/{first['id']}/complete", headers=h_contact,
                        json={"action": "approve"}).json()
    assert final["status"] == "running"
    # missing form value -> clear 400
    bad = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "stage_c_form", "title": "缺联系人", "variables": {}})
    assert bad.status_code == 400 and "f_contact" in bad.json()["detail"]


def test_trigger_node_fires_webhook(client, admin_headers):
    boss = make_user(client, "t_boss", name="主管")
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "审批",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
        "childNode": {
            "type": "TRIGGER", "name": "通知ERP",
            "props": {"url": "https://erp.example.com/hook", "method": "POST"},
            "childNode": None,
        }}}
    definition = _deploy(client, admin_headers, tree, [], "stage_c_trigger")

    class FakeResp:
        status_code = 200

        def json(self):
            return {"errcode": 0}

    with patch("httpx.post", return_value=FakeResp()) as mock:
        ticket = client.post("/approvals", headers=admin_headers, json={
            "definition_key": "stage_c_trigger", "title": "带触发器"}).json()
        # first pending is the approval; trigger sits after it
        assert not [t for t in ticket["tasks"] if t["action"] == "trigger"]

        row = [t for t in ticket["tasks"] if t["status"] == "pending"][0]
        done = client.post(f"/approvals/tasks/{row['id']}/complete", headers=admin_headers,
                           json={"action": "approve"}).json()
        fired = [t for t in done["tasks"] if t["action"] == "trigger"]
        assert len(fired) == 1 and "HTTP 200" in fired[0]["comment"]
        assert mock.call_count == 1
        assert done["status"] == "approved", "trigger must not block completion"


def test_timeout_reminder_marks_overdue(client, admin_headers):
    from datetime import timedelta

    from app.models import utcnow
    from app.services import reminder as reminder_mod

    boss = make_user(client, "r_boss", name="慢主管")
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "限时审批",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any",
                  "timeout": {"enabled": True, "unit": "H", "value": 2}},
        "childNode": None}}
    _deploy(client, admin_headers, tree, [], "stage_c_timeout")

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "stage_c_timeout", "title": "限时单"}).json()

    db = SessionLocal()
    try:
        row = (db.query(ApprovalTask)
               .filter(ApprovalTask.ticket_id == ticket["id"], ApprovalTask.status == "pending")
               .first())
        assert row.due_at is not None
        # force overdue
        row.due_at = utcnow() - timedelta(minutes=1)
        db.commit()

        with patch.object(reminder_mod, "send_wecom_text", return_value=False) as mock_push:
            count = reminder_mod.remind_overdue()
        assert count >= 1
        assert mock_push.call_count >= 1  # attempted wecom push
        db.refresh(row)
        assert row.reminded_at is not None

        # second run within interval -> no duplicate
        assert reminder_mod.remind_overdue() == 0
    finally:
        db.close()


def test_detail_returns_form_with_perms(client, admin_headers):
    boss = make_user(client, "p_boss", name="主管")
    form = [
        {"id": "f_amt", "name": "AmountInput", "title": "金额", "valueType": "Number",
         "props": {"required": True}},
        {"id": "f_secret", "name": "TextInput", "title": "内部编号", "valueType": "String",
         "props": {"required": False}},
    ]
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "主管",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any",
                  "formPerms": {"f_secret": "hidden"}},
        "childNode": None}}
    _deploy(client, admin_headers, tree, form, "stage_c_perms")

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "stage_c_perms", "title": "权限单",
        "variables": {"f_amt": 100, "f_secret": "S-001"}}).json()
    assert ticket["form_items"] and ticket["form_values"]["f_amt"] == 100
