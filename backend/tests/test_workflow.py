"""Multi-workflow engine tests: CRUD, project binding, handler rules, task migration."""


def _list(client, headers):
    return client.get("/workflows", headers=headers).json()


def _create_bugfix_wf(client, headers, name="缺陷处理流"):
    nodes = [
        {"key": "open", "name": "待处理", "color": "#F56C6C", "x": 60, "y": 120, "is_initial": True,
         "is_done": False, "next_keys": ["fixing"], "handler_type": "any", "handler_user_ids": []},
        {"key": "fixing", "name": "修复中", "color": "#409EFF", "x": 340, "y": 120, "is_initial": False,
         "is_done": False, "next_keys": ["verify"], "handler_type": "any", "handler_user_ids": []},
        {"key": "verify", "name": "待验证", "color": "#E6A23C", "x": 620, "y": 120, "is_initial": False,
         "is_done": False, "next_keys": ["closed"], "handler_type": "assignee", "handler_user_ids": []},
        {"key": "closed", "name": "已关闭", "color": "#67C23A", "x": 900, "y": 120, "is_initial": False,
         "is_done": True, "next_keys": [], "handler_type": "admins", "handler_user_ids": []},
    ]
    resp = client.post("/workflows", headers=headers,
                       json={"name": name, "description": "bug 专用", "nodes": nodes})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_default_workflow_seeded(client, admin_headers):
    wfs = _list(client, admin_headers)
    assert len(wfs) >= 1
    default = [w for w in wfs if w["is_default"]][0]
    assert default["name"] == "默认工作流"
    detail = client.get(f"/workflows/{default['id']}", headers=admin_headers).json()
    keys = [n["key"] for n in detail["nodes"]]
    assert keys == ["todo", "in_progress", "testing", "done"]
    assert detail["nodes"][0]["is_initial"] is True


def test_workflow_crud_and_guard(client, admin_headers):
    wf = _create_bugfix_wf(client, admin_headers)
    assert len(wf["nodes"]) == 4

    # duplicate name rejected
    dup = client.post("/workflows", headers=admin_headers,
                      json={"name": "缺陷处理流", "nodes": []})
    assert dup.status_code == 400

    # rename + edit nodes via save
    nodes = [dict(n) for n in wf["nodes"]]
    nodes.append({"key": "reopen", "name": "重新打开", "color": "#123456", "x": 60, "y": 300,
                  "is_initial": False, "is_done": False, "next_keys": ["fixing"],
                  "handler_type": "members", "handler_user_ids": [admin_headers and 1]})
    resp = client.put(f"/workflows/{wf['id']}", headers=admin_headers,
                      json={"name": "缺陷处理流V2", "description": "d", "nodes": nodes})
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/workflows/{wf['id']}", headers=admin_headers).json()
    assert detail["name"] == "缺陷处理流V2"
    assert len(detail["nodes"]) == 5

    # default workflow cannot be deleted
    default_id = [w for w in _list(client, admin_headers) if w["is_default"]][0]["id"]
    assert client.delete(f"/workflows/{default_id}", headers=admin_headers).status_code == 400

    # unbound workflow can be deleted
    assert client.delete(f"/workflows/{wf['id']}", headers=admin_headers).status_code == 200


def test_workflow_requires_admin_to_write(client):
    from tests.conftest import make_user, login_as

    make_user(client, "wflowuser2")
    h = login_as(client, "wflowuser2")
    assert client.post("/workflows", headers=h, json={"name": "x"}).status_code == 403


def test_project_bind_workflow_and_flow_rules(client, admin_headers):
    from tests.conftest import make_user, login_as

    wf = _create_bugfix_wf(client, admin_headers)
    pid = client.post("/projects", headers=admin_headers, json={"key": "BUGPRJ", "name": "缺陷项目"}).json()["id"]

    # bind
    bind = client.put(f"/projects/{pid}/workflow", headers=admin_headers, json={"workflow_id": wf["id"]})
    assert bind.status_code == 200, bind.text
    assert client.get(f"/projects/{pid}/workflow", headers=admin_headers).json()["id"] == wf["id"]

    # task created on custom initial status
    t = client.post(f"/projects/{pid}/tasks", headers=admin_headers,
                    json={"title": "登录崩溃", "type": "bug"}).json()
    assert t["status"] == "open"

    # open -> verify is not allowed by edges
    r = client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"status": "verify"})
    assert r.status_code == 400

    # open -> fixing OK
    assert client.put(f"/tasks/{t['id']}", headers=admin_headers,
                      json={"status": "fixing"}).json()["status"] == "fixing"

    # handler rules (superuser bypasses, so test with plain members)
    zs = make_user(client, "handler_zs", name="张三")
    ls = make_user(client, "handler_ls", name="李四")
    client.post(f"/projects/{pid}/members", headers=admin_headers, json={"user_id": zs["id"]})
    client.post(f"/projects/{pid}/members", headers=admin_headers, json={"user_id": ls["id"]})
    hzs = login_as(client, "handler_zs")
    hls = login_as(client, "handler_ls")
    client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"assignee_id": zs["id"]})

    # ensure task is on fixing
    client.put(f"/tasks/{t['id']}", headers=admin_headers, json={"status": "fixing"})

    # verify node requires the assignee: li si (not assignee) forbidden
    r403 = client.put(f"/tasks/{t['id']}", headers=hls, json={"status": "verify"})
    assert r403.status_code == 403
    assert "负责人" in r403.json()["detail"]
    # zhang san (assignee) allowed
    ok = client.put(f"/tasks/{t['id']}", headers=hzs, json={"status": "verify"})
    assert ok.status_code == 200, ok.text

    # closed node requires project admin: member forbidden, project admin allowed
    forbidden = client.put(f"/tasks/{t['id']}", headers=hzs, json={"status": "closed"})
    assert forbidden.status_code == 403
    assert "管理员" in forbidden.json()["detail"]
    members = client.get(f"/projects/{pid}/members", headers=admin_headers).json()
    ls_member = [m for m in members if m["user_id"] == ls["id"]][0]
    client.put(f"/projects/{pid}/members/{ls_member['id']}", headers=admin_headers,
               json={"role": "admin"})
    closed = client.put(f"/tasks/{t['id']}", headers=hls, json={"status": "closed"})
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"


def test_switch_workflow_migrates_orphan_tasks(client, admin_headers):
    wf = _create_bugfix_wf(client, admin_headers, name="切换目标流")
    pid = client.post("/projects", headers=admin_headers, json={"key": "SWF", "name": "切换"}).json()["id"]
    t = client.post(f"/projects/{pid}/tasks", headers=admin_headers, json={"title": "旧状态任务"}).json()
    assert t["status"] == "todo"  # default workflow initial

    resp = client.put(f"/projects/{pid}/workflow", headers=admin_headers, json={"workflow_id": wf["id"]})
    assert resp.json()["migrated"] >= 1
    after = client.get(f"/tasks/{t['id']}", headers=admin_headers).json()
    assert after["status"] == "open"  # migrated to new initial

    # unbind -> back to default, orphan open -> todo
    resp2 = client.put(f"/projects/{pid}/workflow", headers=admin_headers, json={"workflow_id": None})
    assert resp2.json()["migrated"] >= 1
    assert client.get(f"/tasks/{t['id']}", headers=admin_headers).json()["status"] == "todo"


def test_delete_bound_workflow_rejected(client, admin_headers):
    wf = _create_bugfix_wf(client, admin_headers, name="被绑定流")
    pid = client.post("/projects", headers=admin_headers, json={"key": "BDW", "name": "绑定"}).json()["id"]
    client.put(f"/projects/{pid}/workflow", headers=admin_headers, json={"workflow_id": wf["id"]})
    resp = client.delete(f"/workflows/{wf['id']}", headers=admin_headers)
    assert resp.status_code == 400
    assert "项目" in resp.json()["detail"]
