"""Admin panel API tests: permission, user CRUD, disable/re-enable, password reset."""
from fastapi import status


def test_admin_stats_requires_superuser(client):
    resp = client.get("/admin/stats")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_stats(client, admin_headers):
    body = client.get("/admin/stats", headers=admin_headers).json()
    assert body["user_count"] >= 1
    assert body["project_count"] >= 1
    assert "auth_options" in body
    assert set(body["task_status_distribution"]) == {"todo", "in_progress", "testing", "done"}


def test_admin_create_and_update_user(client, admin_headers):
    # create
    resp = client.post("/admin/users", headers=admin_headers,
                       json={"username": "NewUser", "name": "新用户", "password": "abc12345"})
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["username"] == "newuser"
    assert user["auth_type"] == "local"

    # new user can login
    login = client.post("/auth/login", json={"username": "newuser", "password": "abc12345"})
    assert login.status_code == 200

    # duplicate rejected
    dup = client.post("/admin/users", headers=admin_headers,
                      json={"username": "newuser", "password": "abc12345"})
    assert dup.status_code == 400

    # reset password
    upd = client.put(f"/admin/users/{user['id']}", headers=admin_headers, json={"password": "xyz98765"})
    assert upd.status_code == 200
    assert client.post("/auth/login", json={"username": "newuser", "password": "abc12345"}).status_code == 401
    assert client.post("/auth/login", json={"username": "newuser", "password": "xyz98765"}).status_code == 200

    # grant superuser
    grant = client.put(f"/admin/users/{user['id']}", headers=admin_headers, json={"is_superuser": True})
    assert grant.json()["is_superuser"] is True


def test_admin_disable_user_blocks_login(client, admin_headers):
    from tests.conftest import make_user, login_as

    user = make_user(client, "disableme")
    headers_before = login_as(client, "disableme")
    assert client.get("/auth/me", headers=headers_before).status_code == 200

    resp = client.put(f"/admin/users/{user['id']}", headers=admin_headers, json={"is_active": False})
    assert resp.status_code == 200

    # login rejected even with correct password
    bad = client.post("/auth/login", json={"username": "disableme", "password": "pass123"})
    assert bad.status_code == 401

    # re-enable restores login
    client.put(f"/admin/users/{user['id']}", headers=admin_headers, json={"is_active": True})
    # password was dropped on disable -> admin must reset it
    assert client.post("/auth/login", json={"username": "disableme", "password": "pass123"}).status_code == 401
    client.put(f"/admin/users/{user['id']}", headers=admin_headers, json={"password": "newpass123"})
    ok = client.post("/auth/login", json={"username": "disableme", "password": "newpass123"})
    assert ok.status_code == 200


def test_admin_cannot_modify_self_or_last_superuser(client, admin_headers):
    me = client.get("/auth/me", headers=admin_headers).json()
    assert client.put(f"/admin/users/{me['id']}", headers=admin_headers,
                      json={"is_active": False}).status_code == 400


def test_admin_requires_superuser(client):
    from tests.conftest import make_user, login_as

    make_user(client, "plainuser")
    headers = login_as(client, "plainuser")
    assert client.get("/admin/stats", headers=headers).status_code == 403
    assert client.get("/admin/users", headers=headers).status_code == 403


def test_admin_user_search_and_project_count(client, admin_headers):
    from tests.conftest import make_user

    make_user(client, "countme", name="计数用户")
    body = client.get("/admin/users", params={"q": "计数"}, headers=admin_headers).json()
    assert any(u["username"] == "countme" for u in body)
    assert all("project_count" in u for u in body)
