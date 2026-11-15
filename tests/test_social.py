"""需求 5、6：收藏与留言（含卖家回复）。"""
from app.db import get_db
from tests.helpers import add_item, add_user, login


def test_favorite_toggle(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller, title="想收藏的台灯")
    login(client, "buyer")

    response = client.post("/items/%d/favorite" % item_id, follow_redirects=True)
    assert "已收藏".encode("utf-8") in response.data
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM favorite").fetchone()[0]
    assert count == 1

    response = client.post("/items/%d/favorite" % item_id, follow_redirects=True)
    assert "已取消收藏".encode("utf-8") in response.data
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM favorite").fetchone()[0]
    assert count == 0


def test_favorites_page_lists_items(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller, title="收藏列表里的教材")
    login(client, "buyer")
    client.post("/items/%d/favorite" % item_id)
    response = client.get("/favorites")
    assert "收藏列表里的教材".encode("utf-8") in response.data


def test_leave_message(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller)
    login(client, "buyer")

    response = client.post("/items/%d/messages" % item_id,
                           data={"content": "还在吗？"}, follow_redirects=True)
    assert "留言成功".encode("utf-8") in response.data
    assert "还在吗？".encode("utf-8") in response.data


def test_empty_message_rejected(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller)
    login(client, "buyer")
    response = client.post("/items/%d/messages" % item_id, data={"content": "   "},
                           follow_redirects=True)
    assert "留言不能为空".encode("utf-8") in response.data


def test_seller_can_reply(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller)
    login(client, "buyer")
    client.post("/items/%d/messages" % item_id, data={"content": "能便宜吗？"})
    with app.app_context():
        parent_id = get_db().execute("SELECT id FROM message").fetchone()[0]

    login(client, "seller")
    response = client.post("/items/%d/messages" % item_id,
                           data={"content": "可以少 2 元", "parent_id": parent_id},
                           follow_redirects=True)
    assert "回复成功".encode("utf-8") in response.data
    assert "可以少 2 元".encode("utf-8") in response.data
    assert "卖家回复".encode("utf-8") in response.data


def test_non_seller_cannot_reply(client, app):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    add_user(app, "third")
    item_id = add_item(app, seller)
    login(client, "buyer")
    client.post("/items/%d/messages" % item_id, data={"content": "想问下成色"})
    with app.app_context():
        parent_id = get_db().execute("SELECT id FROM message").fetchone()[0]

    login(client, "third")
    response = client.post("/items/%d/messages" % item_id,
                           data={"content": "我也来插一句", "parent_id": parent_id},
                           follow_redirects=True)
    assert "只有发布者可以回复".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM message").fetchone()[0] == 1
