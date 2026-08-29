"""LDAP / WeCom authentication tests with mocked external services."""
from unittest.mock import patch

from app.core.config import settings


def _profile_wecom():
    return {"userid": "zhangwei", "name": "张伟", "email": "zhangwei@corp.com", "avatar": ""}


def test_wecom_login_provisions_user(client, monkeypatch):
    monkeypatch.setattr(settings, "WECOM_ENABLED", True)

    class FakeProfile:
        def __init__(self, result):
            self.result = result

    with patch("app.services.wecom_service.login_with_code", return_value=_profile_wecom()):
        resp = client.post("/auth/wecom", json={"code": "mock-code"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["username"] == "wecom_zhangwei"
    assert body["user"]["name"] == "张伟"
    assert body["user"]["auth_type"] == "wecom"

    # second login returns the same user (no duplicates)
    with patch("app.services.wecom_service.login_with_code", return_value=_profile_wecom()):
        resp2 = client.post("/auth/wecom", json={"code": "mock-code-2"})
    assert resp2.status_code == 200
    assert resp2.json()["user"]["id"] == body["user"]["id"]

    # token works
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["email"] == "zhangwei@corp.com"


def test_wecom_login_disabled(client):
    resp = client.post("/auth/wecom", json={"code": "x"})
    assert resp.status_code == 400


def test_ldap_login_provisions_user(client, monkeypatch):
    from app.services.ldap_service import LDAPAuthResult

    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    ldap_result = LDAPAuthResult(username="wangfang", name="王芳", email="wangfang@corp.com",
                                 dn="uid=wangfang,ou=people,dc=example,dc=com")

    with patch("app.services.ldap_service.authenticate", return_value=ldap_result):
        resp = client.post("/auth/login", json={"username": "wangfang", "password": "ldapsecret"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["auth_type"] == "ldap"
    assert body["user"]["name"] == "王芳"

    # password fallback no longer works for ldap user (no local hash)
    with patch("app.services.ldap_service.authenticate", return_value=None):
        bad = client.post("/auth/login", json={"username": "wangfang", "password": "wrong"})
    assert bad.status_code == 401


def test_login_falls_back_to_ldap(client, monkeypatch):
    """Local user with wrong password + valid LDAP creds => LDAP login succeeds."""
    from app.services.ldap_service import LDAPAuthResult

    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    result = LDAPAuthResult(username="newldap", name="新用户", email="", dn="uid=newldap,dc=x")

    with patch("app.services.ldap_service.authenticate", return_value=result):
        resp = client.post("/auth/login", json={"username": "newldap", "password": "pw"})
    assert resp.status_code == 200
    assert resp.json()["user"]["auth_type"] == "ldap"
