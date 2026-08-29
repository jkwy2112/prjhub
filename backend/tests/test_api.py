"""Core API tests: auth, projects, git repo init, tasks workflow, members, dashboard."""


def test_health_and_auth_options(client):
    assert client.get("/health").json()["status"] == "ok"
    opts = client.get("/meta/auth-options").json()
    assert opts == {"ldap_enabled": False, "wecom_enabled": False}


def test_local_login_success(client, admin_headers):
    me = client.get("/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["is_superuser"] is True
    assert me.json()["username"] == "admin"


def test_local_login_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "bad"})
    assert resp.status_code == 401


def test_unauthorized_without_token(client):
    assert client.get("/projects").status_code == 401


def test_create_project_inits_git_repo(client, admin_headers):
    resp = client.post("/projects", headers=admin_headers,
                       json={"key": "APITEST", "name": "API测试项目", "init_git_repo": True})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["key"] == "APITEST"
    assert body["my_role"] == "owner"
    assert body["repo_path"].endswith("APITEST.git")
    import os
    assert os.path.exists(os.path.join(body["repo_path"], "HEAD")), "bare repo must exist on disk"


def test_create_project_duplicate_key(client, admin_headers):
    r1 = client.post("/projects", headers=admin_headers, json={"key": "DUP", "name": "p1"})
    assert r1.status_code == 201
    r2 = client.post("/projects", headers=admin_headers, json={"key": "DUP", "name": "p2"})
    assert r2.status_code == 400


def test_project_invalid_key_rejected(client, admin_headers):
    resp = client.post("/projects", headers=admin_headers, json={"key": "bad-key", "name": "x"})
    assert resp.status_code == 422


def test_task_workflow_and_invalid_transition(client, admin_headers):
    pid = client.post("/projects", headers=admin_headers,
                      json={"key": "FLOW", "name": "流程测试"}).json()["id"]

    t = client.post(f"/projects/{pid}/tasks", headers=admin_headers,
                    json={"title": "登录功能开发", "type": "requirement", "priority": "high"})
    assert t.status_code == 201, t.text
    task = t.json()
    assert task["number"] >= 1

    # todo -> testing is not allowed
    bad = client.put(f"/tasks/{task['id']}", headers=admin_headers, json={"status": "testing"})
    assert bad.status_code == 400

    # todo -> in_progress -> testing -> done is allowed
    for s in ("in_progress", "testing", "done"):
        ok = client.put(f"/tasks/{task['id']}", headers=admin_headers, json={"status": s})
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == s


def test_task_comment_and_detail(client, admin_headers):
    pid = client.post("/projects", headers=admin_headers, json={"key": "CMT", "name": "评论"}).json()["id"]
    tid = client.post(f"/projects/{pid}/tasks", headers=admin_headers, json={"title": "t"}).json()["id"]

    c = client.post(f"/tasks/{tid}/comments", headers=admin_headers, json={"content": "看起来不错"})
    assert c.status_code == 201
    detail = client.get(f"/tasks/{tid}", headers=admin_headers).json()
    assert len(detail["comments"]) == 1
    assert detail["comments"][0]["content"] == "看起来不错"
    assert detail["comments"][0]["user"]["username"] == "admin"


def test_member_add_and_permission(client, admin_headers):
    from tests.conftest import make_user, login_as

    pid = client.post("/projects", headers=admin_headers, json={"key": "MEM", "name": "成员"}).json()["id"]
    user = make_user(client, "zhangsan", name="张三")
    zs = login_as(client, "zhangsan")

    # non-member cannot read project
    assert client.get(f"/projects/{pid}", headers=zs).status_code == 403

    # admin adds zhangsan as member
    add = client.post(f"/projects/{pid}/members", headers=admin_headers,
                      json={"user_id": user["id"], "role": "member"})
    assert add.status_code == 201, add.text

    # now zhangsan can read and create task
    assert client.get(f"/projects/{pid}", headers=zs).status_code == 200
    t = client.post(f"/projects/{pid}/tasks", headers=zs, json={"title": "张三的任务", "assignee_id": user["id"]})
    assert t.status_code == 201

    # member cannot manage members
    other = make_user(client, "lisi")
    assert client.post(f"/projects/{pid}/members", headers=zs, json={"user_id": other["id"]}).status_code == 403

    # my tasks shows assigned task
    mine = client.get("/my/tasks", headers=zs)
    assert any(item["title"] == "张三的任务" for item in mine.json())


def test_dashboard(client, admin_headers):
    d = client.get("/dashboard", headers=admin_headers)
    assert d.status_code == 200
    body = d.json()
    assert body["project_count"] >= 1
    assert set(body["status_distribution"].keys()) == {"todo", "in_progress", "testing", "done", "other"}


def test_project_delete_removes_repo(client, admin_headers):
    import os

    p = client.post("/projects", headers=admin_headers, json={"key": "DEL", "name": "待删除"}).json()
    assert os.path.exists(p["repo_path"])
    resp = client.delete(f"/projects/{p['id']}", headers=admin_headers)
    assert resp.status_code == 204
    assert not os.path.exists(p["repo_path"])
    assert client.get(f"/projects/{p['id']}", headers=admin_headers).status_code == 404
