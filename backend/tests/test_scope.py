"""Template visible-scope tests: all / dept / user filtering on launch list."""
from app.db import SessionLocal
from app.models import User
from tests.conftest import login_as, make_user


def _deploy(client, headers, key, scope, depts=None, users_=None):
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "审批",
        "props": {"assigneeType": "users", "users": [1], "mode": "any"}, "childNode": None}}
    payload = {"key": key, "name": key, "tree": tree,
               "visible_scope": scope, "visible_depts": depts or [], "visible_user_ids": users_ or []}
    resp = client.post("/approvals/definitions/tree", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_scope_validation(client, admin_headers):
    tree = {"type": "ROOT", "childNode": None}
    bad = client.post("/approvals/definitions/tree", headers=admin_headers,
                      json={"key": "s_bad", "name": "x", "tree": {"type": "ROOT", "childNode": {
                          "type": "APPROVAL", "name": "a",
                          "props": {"assigneeType": "users", "users": [1], "mode": "any"}, "childNode": None}},
                          "visible_scope": "dept", "visible_depts": []})
    assert bad.status_code == 400
    bad2 = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "s_bad2", "name": "x", "tree": {"type": "ROOT", "childNode": {
                           "type": "APPROVAL", "name": "a",
                           "props": {"assigneeType": "users", "users": [1], "mode": "any"}, "childNode": None}},
                           "visible_scope": "user", "visible_user_ids": []})
    assert bad2.status_code == 400
    bad3 = client.post("/approvals/definitions/tree", headers=admin_headers,
                       json={"key": "s_bad3", "name": "x", "tree": {"type": "ROOT", "childNode": {
                           "type": "APPROVAL", "name": "a",
                           "props": {"assigneeType": "users", "users": [1], "mode": "any"}, "childNode": None}},
                           "visible_scope": "user", "visible_user_ids": [99999]})
    assert bad3.status_code == 400 and "不存在" in bad3.json()["detail"]


def test_dept_and_user_scope_filtering(client, admin_headers):
    fin = make_user(client, "sc_fin", name="财务员工")
    tech = make_user(client, "sc_tech", name="技术员工")
    outsider = make_user(client, "sc_out", name="局外人")

    db = SessionLocal()
    try:
        db.query(User).filter(User.id == fin["id"]).update({"dept": "财务部"})
        db.query(User).filter(User.id == tech["id"]).update({"dept": "技术部"})
        db.commit()
    finally:
        db.close()

    _deploy(client, admin_headers, "sc_dept_flow", "dept", depts=["财务部"])
    _deploy(client, admin_headers, "sc_user_flow", "user", users_=[tech["id"]])

    def keys_as(headers):
        return {d["key"] for d in client.get("/approvals/definitions", headers=headers).json()}

    # 财务员工: sees dept flow, not user flow
    h_fin = login_as(client, "sc_fin")
    k = keys_as(h_fin)
    assert "sc_dept_flow" in k and "sc_user_flow" not in k

    # 技术员工: sees user flow, not dept flow
    h_tech = login_as(client, "sc_tech")
    k2 = keys_as(h_tech)
    assert "sc_user_flow" in k2 and "sc_dept_flow" not in k2

    # 局外人(no dept, not in list): sees neither
    h_out = login_as(client, "sc_out")
    k3 = keys_as(h_out)
    assert "sc_dept_flow" not in k3 and "sc_user_flow" not in k3

    # superuser sees all
    k4 = keys_as(admin_headers)
    assert {"sc_dept_flow", "sc_user_flow"} <= k4


def test_meta_depts(client, admin_headers):
    make_user(client, "md_a")
    db = SessionLocal()
    try:
        db.query(User).filter(User.username == "md_a").update({"dept": "研发中心"})
        db.commit()
    finally:
        db.close()
    resp = client.get("/meta/depts", headers=admin_headers)
    assert resp.status_code == 200
    assert "研发中心" in resp.json()
