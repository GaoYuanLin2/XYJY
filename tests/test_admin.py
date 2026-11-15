"""需求 8：后台审核（通过/驳回）、下架与权限。"""
from app.db import get_db
from tests.helpers import add_item, add_user, item_form, login


def test_admin_requires_admin_role(client, app):
    add_user(app, "normal")
    login(client, "normal")
    response = client.get("/admin/", follow_redirects=True)
    assert "需要管理员权限".encode("utf-8") in response.data


def test_admin_page_lists_pending(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    add_item(app, seller, status="pending", title="等审核的插线板")
    login(client, "admin1")
    response = client.get("/admin/")
    assert "等审核的插线板".encode("utf-8") in response.data


def test_approve_makes_item_visible(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, status="pending", title="通过审核的商品")
    login(client, "admin1")

    response = client.post("/admin/items/%d/approve" % item_id, follow_redirects=True)
    assert "已通过审核".encode("utf-8") in response.data
    with app.app_context():
        row = get_db().execute("SELECT status, review_note FROM item WHERE id = ?",
                               (item_id,)).fetchone()
    assert row["status"] == "approved"
    assert "审核通过" in row["review_note"]
    assert "通过审核的商品".encode("utf-8") in client.get("/").data


def test_reject_requires_note(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, status="pending", title="信息不全的商品")
    login(client, "admin1")

    response = client.post("/admin/items/%d/reject" % item_id, data={"note": ""},
                           follow_redirects=True)
    assert "必须填写原因".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT status FROM item WHERE id = ?",
                                (item_id,)).fetchone()[0] == "pending"


def test_reject_with_note(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, status="pending", title="缺价格的商品")
    login(client, "admin1")
    response = client.post("/admin/items/%d/reject" % item_id,
                           data={"note": "描述太简单，请补充成色"}, follow_redirects=True)
    assert "已驳回".encode("utf-8") in response.data
    with app.app_context():
        row = get_db().execute("SELECT status, review_note FROM item WHERE id = ?",
                               (item_id,)).fetchone()
    assert row["status"] == "rejected"
    assert "描述太简单" in row["review_note"]


def test_admin_can_offline_item(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, status="approved", title="需要下架的商品")
    login(client, "admin1")
    response = client.post("/admin/items/%d/offline" % item_id, follow_redirects=True)
    assert "已下架".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT status FROM item WHERE id = ?",
                                (item_id,)).fetchone()[0] == "offline"


def test_rejected_item_resubmitted_after_edit(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, status="rejected", title="被打回的商品")
    login(client, "seller")
    client.post("/items/%d/edit" % item_id, data=item_form({"title": "补齐信息后的商品"}),
                follow_redirects=True)
    with app.app_context():
        assert get_db().execute("SELECT status FROM item WHERE id = ?",
                                (item_id,)).fetchone()[0] == "pending"


def test_admin_stats(client, app):
    add_user(app, "admin1", role="admin")
    seller = add_user(app, "seller")
    add_item(app, seller, status="pending", title="待审核")
    add_item(app, seller, status="approved", title="在售")
    login(client, "admin1")
    response = client.get("/admin/")
    assert "待审核商品".encode("utf-8") in response.data
    assert "在售商品".encode("utf-8") in response.data
