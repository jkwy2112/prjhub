"""Customizable workflow tests."""
from app.db import SessionLocal
from app.services import config_service


def _get(client, headers):
    return client.get("/workflow", headers=headers).json()


def test_default_workflow_seeded(client, admin_headers):
    wf = _get(client, admin_headers)
    keys = [s["key"] for s in wf["statuses"]]
    assert keys == ["todo", "in_progress", "testing", "done"]
    assert wf["statuses"][0]["is_initial"] is True
    assert wf["statuses"][-1]["is_done"] is True


def test_workflow_requires_admin_to_write(client):
    from tests.conftest import make_user, login_as

    make_user(client, "wflowuser")
    h = login_as(client, "wflowuser")
    assert client.put("/workflow", headers=h, json={"statuses": []}).status_code == 403


def test_customize_workflow_add_status_and_transitions(client, admin_headers):
    # add a new status "code_review" between in_progress and testing
    wf = _get(client, admin_headers)
    statuses = wf["statuses"]
    payload = [
        {"key": "todo", "name": "待办", "color": "#909399", "is_initial": True, "is_done": False,
         "next_keys": ["in_progress"]},
        {"key": "in_progress", "name": "开发中", "color": "#409EFF", "is_initial": False, "is_done": False,
         "next_keys": ["code_review"]},
        {"key": "code_review", "name": "代码评审", "color": "#9254de", "is_initial": False, "is_done": False,
         "next_keys": ["testing", "done"]},
        {"key": "testing", "name": "测试中", "color": "#E6A23C", "is_initial": False, "is_done": False,
         "next_keys": ["done"]},
        {"key": "done", "name": "已完成", "color": "#67C23A", "is_initial": False, "is_done": True,
         "next_keys": []},
    ]
    resp = client.put("/workflow", headers=admin_headers, json={"statuses": payload})
    assert resp.status_code == 200, resp.text

    wf2 = _get(client, admin_headers)
    assert [s["key"] for s in wf2["statuses"]] == [p["key"] for p in payload]
    assert wf2["statuses"][2]["name"] == "代码评审"

    # task flow follows the new rules: todo -> testing now invalid, todo -> code_review invalid too
    pid = client.post("/projects", headers=admin_headers, json={"key": "WF", "name": "工作流"}).json()["id"]
    t = client.post(f"/projects/{pid}/tasks", headers=admin_headers, json={"title": "t"}).json()
    assert t["status"] == "todo"
    assert client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"status": "testing"}).status_code == 400
    ok = client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"status": "in_progress"})
    assert ok.status_code == 200
    ok2 = client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"status": "code_review"})
    assert ok2.status_code == 200
    assert ok2.json()["status"] == "code_review"
    # kanban grouping respects custom statuses
    tasks = client.get(f"/projects/{pid}/tasks", headers=admin_headers).json()
    assert all(x["status"] in {s["key"] for s in payload} for x in tasks)


def test_delete_status_migrates_tasks_to_initial(client, admin_headers):
    pid = client.post("/projects", headers=admin_headers, json={"key": "WFD", "name": "删除状态"}).json()["id"]
    t = client.post(f"/projects/{pid}/tasks", headers=admin_headers, json={"title": "占用状态"}).json()
    assert t["status"] == "todo"

    wf = _get(client, admin_headers)
    payload = [dict(s) for s in wf["statuses"] if s["key"] != "todo"]
    payload[0]["is_initial"] = True  # keep single initial
    payload[0]["next_keys"] = [k for k in payload[0]["next_keys"] if k != "todo"]
    for s in payload:  # drop dangling references to removed status
        s["next_keys"] = [k for k in s["next_keys"] if k != "todo"]
    resp = client.put("/workflow", headers=admin_headers, json={"statuses": payload})
    assert resp.status_code == 200, resp.text
    assert resp.json()["migrated"] >= 1

    # orphan task was moved to the new initial status
    after = client.get(f"/tasks/{t['id']}", headers=admin_headers).json()
    assert after["status"] == "in_progress"


def test_workflow_validation_rules(client, admin_headers):
    base = _get(client, admin_headers)["statuses"]

    # two initials rejected
    bad = [dict(s) for s in base]
    bad[1]["is_initial"] = True
    assert client.put("/workflow", headers=admin_headers, json={"statuses": bad}).status_code == 400

    # transition to unknown status rejected
    bad2 = [dict(s) for s in base]
    bad2[0]["next_keys"] = ["nonexistent"]
    assert client.put("/workflow", headers=admin_headers, json={"statuses": bad2}).status_code == 400

    # no initial rejected
    bad3 = [dict(s) for s in base]
    bad3[0]["is_initial"] = False
    assert client.put("/workflow", headers=admin_headers, json={"statuses": bad3}).status_code == 400


def test_reset_workflow(client, admin_headers):
    client.post("/workflow/reset", headers=admin_headers)  # clean baseline (shared test db)
    wf = _get(client, admin_headers)
    custom = [dict(s) for s in wf["statuses"]]
    custom.append({"key": "extra_step", "name": "附加", "color": "#123456", "is_initial": False,
                   "is_done": False, "next_keys": []})
    assert client.put("/workflow", headers=admin_headers, json={"statuses": custom}).status_code == 200
    assert len(_get(client, admin_headers)["statuses"]) == 5

    assert client.post("/workflow/reset", headers=admin_headers).status_code == 200
    assert len(_get(client, admin_headers)["statuses"]) == 4
