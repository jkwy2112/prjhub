"""Admin auth-config APIs: save/override, masking, connection tests (mocked)."""
from unittest.mock import MagicMock, patch

from app.db import SessionLocal
from app.services import config_service


def test_auth_config_requires_admin(client):
    from tests.conftest import make_user, login_as

    make_user(client, "cfguser")
    h = login_as(client, "cfguser")
    assert client.get("/admin/auth-config", headers=h).status_code == 403


def test_save_and_read_ldap_config(client, admin_headers):
    saved = {
        "enabled": True, "server": "ldap://ldap.corp.com:389", "use_ssl": False,
        "bind_dn": "cn=admin,dc=corp,dc=com", "bind_password": "topsecret",
        "search_base": "ou=people,dc=corp,dc=com", "search_filter": "(uid={login})",
        "attr_username": "uid", "attr_display_name": "cn", "attr_email": "mail",
    }
    resp = client.put("/admin/auth-config/ldap", headers=admin_headers, json=saved)
    assert resp.status_code == 200, resp.text

    cfg = client.get("/admin/auth-config", headers=admin_headers).json()["ldap"]
    assert cfg["server"] == "ldap://ldap.corp.com:389"
    assert cfg["bind_dn"] == "cn=admin,dc=corp,dc=com"
    assert cfg["bind_password"] == "******"  # masked
    assert cfg["enabled"] is True

    # effective config used by login flow is unmasked
    db = SessionLocal()
    try:
        eff = config_service.ldap_config(db)
        assert eff["bind_password"] == "topsecret"
        assert eff["search_base"] == "ou=people,dc=corp,dc=com"
    finally:
        db.close()


def test_save_wecom_config(client, admin_headers):
    resp = client.put("/admin/auth-config/wecom", headers=admin_headers, json={
        "enabled": True, "corp_id": "ww123", "corp_secret": "sec", "agent_id": "1000002",
    })
    assert resp.status_code == 200
    cfg = client.get("/admin/auth-config", headers=admin_headers).json()["wecom"]
    assert cfg["corp_id"] == "ww123"
    assert cfg["corp_secret"] == "******"
    assert cfg["enabled"] is True
    assert client.get("/meta/auth-options").json()["wecom_enabled"] is True


def test_masked_secret_resubmission_keeps_stored_value(client, admin_headers):
    client.put("/admin/auth-config/wecom", headers=admin_headers, json={
        "enabled": True, "corp_id": "ww123", "corp_secret": "real-secret", "agent_id": "1"})
    # frontend re-submits the mask -> stored secret must survive
    client.put("/admin/auth-config/wecom", headers=admin_headers, json={
        "enabled": True, "corp_id": "ww456", "corp_secret": "******", "agent_id": "1"})
    db = SessionLocal()
    try:
        eff = config_service.wecom_config(db)
        assert eff["corp_id"] == "ww456"
        assert eff["corp_secret"] == "real-secret"
    finally:
        db.close()


def test_ldap_connection_test_success(client, admin_headers):
    fake_conn = MagicMock()
    with patch("app.services.ldap_service.Connection", return_value=fake_conn) as mock_conn:
        fake_conn.__enter__.return_value = fake_conn
        resp = client.post("/admin/auth-config/ldap/test", headers=admin_headers, json={
            "server": "ldap://ldap.corp.com", "bind_dn": "cn=admin,dc=x", "bind_password": "pw"})
    body = resp.json()
    assert body["ok"] is True
    assert "成功" in body["message"]
    assert mock_conn.call_count == 1


def test_ldap_connection_test_failure(client, admin_headers):
    resp = client.post("/admin/auth-config/ldap/test", headers=admin_headers, json={"server": ""})
    assert resp.json()["ok"] is False


def test_wecom_connection_test(client, admin_headers):
    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    with patch("app.services.wecom_service.httpx.get",
               return_value=FakeResp({"errcode": 0, "access_token": "tok"})):
        ok = client.post("/admin/auth-config/wecom/test", headers=admin_headers, json={
            "corp_id": "ww123", "corp_secret": "sec"})
    assert ok.json()["ok"] is True

    with patch("app.services.wecom_service.httpx.get",
               return_value=FakeResp({"errcode": 40001, "errmsg": "invalid credential"})):
        bad = client.post("/admin/auth-config/wecom/test", headers=admin_headers, json={
            "corp_id": "ww123", "corp_secret": "wrong"})
    body = bad.json()
    assert body["ok"] is False
    assert "40001" in body["message"]
