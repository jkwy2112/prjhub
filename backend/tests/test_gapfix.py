"""Gap-fix tests: User/DateRange conditions, editable form_updates, button permission."""
from tests.conftest import login_as, make_user


def _deploy(client, headers, key, form_items, tree):
    resp = client.post("/approvals/definitions/tree", headers=headers,
                       json={"key": key, "name": key, "tree": tree, "form_items": form_items})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_user_field_condition_routes_by_user_id(client, admin_headers):
    boss = make_user(client, "g_boss", name="主管")
    target = make_user(client, "g_target", name="对接人")
    other = make_user(client, "g_other", name="其他人")

    form = [{"id": "f_contact", "name": "UserPicker", "title": "对接人",
             "valueType": "User", "props": {"required": True, "multiple": False}}]
    tree = {"type": "ROOT", "childNode": {
        "type": "CONDITIONS", "branches": [
            {"type": "CONDITION", "name": "张三分支",
             "props": {"groupsType": "AND", "groups": [{"groupType": "AND", "conditions": [
                 {"field": "f_contact", "valueType": "User", "compare": "==",
                  "value": [target["id"]]}]}]},
             "childNode": {"type": "APPROVAL", "name": "张三专属审批",
                           "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                           "childNode": None}},
            {"type": "CONDITION", "name": "默认", "props": {"groups": []},
             "childNode": {"type": "APPROVAL", "name": "通用审批",
                           "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                           "childNode": None}},
        ], "childNode": None}}
    _deploy(client, admin_headers, "gap_user", form, tree)

    # f_contact = 张三 id -> 张三专属审批
    t1 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_user",
        "variables": {"f_contact": target["id"]}}).json()
    pending1 = [x for x in t1["tasks"] if x["status"] == "pending"]
    assert pending1[0]["node_name"] == "张三专属审批", pending1

    # f_contact = 其他人 id -> 默认分支
    t2 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_user",
        "variables": {"f_contact": other["id"]}}).json()
    pending2 = [x for x in t2["tasks"] if x["status"] == "pending"]
    assert pending2[0]["node_name"] == "通用审批"


def test_daterange_condition_on_start(client, admin_headers):
    boss = make_user(client, "g_d_boss", name="主管D")
    form = [{"id": "f_range", "name": "DateTimeRange", "title": "出差时间",
             "valueType": "DateRange", "props": {"format": "YYYY-MM-DD"}}]
    tree = {"type": "ROOT", "childNode": {
        "type": "CONDITIONS", "branches": [
            {"type": "CONDITION", "name": "九月之后",
             "props": {"groupsType": "AND", "groups": [{"groupType": "AND", "conditions": [
                 {"field": "f_range", "valueType": "DateRange", "compare": ">=",
                  "value": ["2026-09-01"]}]}]},
             "childNode": {"type": "APPROVAL", "name": "旺季审批",
                           "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                           "childNode": None}},
            {"type": "CONDITION", "name": "默认", "props": {"groups": []},
             "childNode": {"type": "APPROVAL", "name": "普通审批",
                           "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                           "childNode": None}},
        ], "childNode": None}}
    _deploy(client, admin_headers, "gap_range", form, tree)

    t1 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_range",
        "variables": {"f_range": ["2026-10-01", "2026-10-05"]}}).json()
    assert [x for x in t1["tasks"] if x["status"] == "pending"][0]["node_name"] == "旺季审批"

    t2 = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_range",
        "variables": {"f_range": ["2026-08-01", "2026-08-03"]}}).json()
    assert [x for x in t2["tasks"] if x["status"] == "pending"][0]["node_name"] == "普通审批"


def test_my_pending_returns_buttons_and_editable(client, admin_headers):
    boss = make_user(client, "g_btn_boss", name="按钮主管")
    form = [{"id": "f_amt", "name": "AmountInput", "title": "金额",
             "valueType": "Number", "props": {"required": True}}]
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "受限审批", "bpmnId": "ut_ap1",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any",
                  "buttons": ["agree", "back_prev"],
                  "formPerms": {"f_amt": "editable"}},
        "childNode": None}}
    _deploy(client, admin_headers, "gap_btn", form, tree)

    client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_btn", "variables": {"f_amt": 100}})

    h = login_as(client, "g_btn_boss")
    pend = client.get("/approvals/my-pending", headers=h).json()
    mine = [p for p in pend if p["ticket"]["definition_key"] == "gap_btn"]
    assert mine, pend
    assert mine[0]["buttons"] == ["agree", "back_prev"]
    assert [f["id"] for f in mine[0]["editable_fields"]] == ["f_amt"]


def test_form_updates_flow_and_affect_later_branch(client, admin_headers):
    boss = make_user(client, "g_ed_boss", name="编辑主管")
    form = [{"id": "f_amt", "name": "AmountInput", "title": "金额",
             "valueType": "Number", "props": {"required": True}}]
    # L1 (f_amt editable) -> gateway on f_amt -> 大额/默认
    tree = {"type": "ROOT", "childNode": {
        "type": "APPROVAL", "name": "初审", "bpmnId": "ut_ap1",
        "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any",
                  "formPerms": {"f_amt": "editable"}},
        "childNode": {
            "type": "CONDITIONS", "branches": [
                {"type": "CONDITION", "name": "大额",
                 "props": {"groupsType": "AND", "groups": [{"groupType": "AND", "conditions": [
                     {"field": "f_amt", "valueType": "Number", "compare": ">", "value": [1000]}]}]},
                 "childNode": {"type": "APPROVAL", "name": "大额终审",
                               "props": {"assigneeType": "users", "users": [boss["id"]], "mode": "any"},
                               "childNode": None}},
                {"type": "CONDITION", "name": "默认", "props": {"groups": []}, "childNode": None},
            ], "childNode": None}}}
    _deploy(client, admin_headers, "gap_edit", form, tree)

    ticket = client.post("/approvals", headers=admin_headers, json={
        "definition_key": "gap_edit", "variables": {"f_amt": 100}}).json()
    row = [t for t in ticket["tasks"] if t["status"] == "pending"][0]

    h = login_as(client, "g_ed_boss")
    done = client.post(f"/approvals/tasks/{row['id']}/complete", headers=h, json={
        "action": "approve", "comment": "改一下金额",
        "form_updates": {"f_amt": 5000}}).json()

    assert done["status"] == "running"
    # edited value changed the branch: 大额终审 pending now
    names = [t["node_name"] for t in done["tasks"] if t["status"] == "pending"]
    assert "大额终审" in names, names
    # ticket variables updated
    detail = client.get(f"/approvals/{ticket['id']}", headers=admin_headers).json()
    assert detail["form_values"]["f_amt"] == 5000
