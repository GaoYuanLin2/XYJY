"""需求 7：订单状态流转（状态机 + 角色校验）。"""
from app.db import get_db
from tests.helpers import add_item, add_user, login


def _order_status(app, order_id):
    with app.app_context():
        return get_db().execute(
            "SELECT status FROM trade_order WHERE id = ?", (order_id,)
        ).fetchone()["status"]


def _create_order(client, app, item_status="approved"):
    seller = add_user(app, "seller")
    add_user(app, "buyer")
    item_id = add_item(app, seller, status=item_status, title="要下单的键盘")
    login(client, "buyer")
    response = client.post("/items/%d/order" % item_id, follow_redirects=True)
    return seller, item_id, response


def test_create_order(client, app):
    seller, item_id, response = _create_order(client, app)
    assert "等待卖家确认".encode("utf-8") in response.data
    with app.app_context():
        order = get_db().execute("SELECT * FROM trade_order").fetchone()
    assert order["status"] == "pending"
    assert order["item_id"] == item_id
    assert order["seller_id"] == seller


def test_cannot_order_own_item(client, app):
    seller = add_user(app, "seller")
    item_id = add_item(app, seller, title="自己的东西")
    login(client, "seller")
    response = client.post("/items/%d/order" % item_id, follow_redirects=True)
    assert "不能购买自己".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM trade_order").fetchone()[0] == 0


def test_cannot_order_unapproved_item(client, app):
    seller, item_id, response = _create_order(client, app, item_status="pending")
    assert "不可下单".encode("utf-8") in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM trade_order").fetchone()[0] == 0


def test_duplicate_active_order_blocked(client, app):
    seller, item_id, _ = _create_order(client, app)
    add_user(app, "buyer2")
    login(client, "buyer2")
    response = client.post("/items/%d/order" % item_id, follow_redirects=True)
    assert "进行中的订单".encode("utf-8") in response.data


def test_full_flow_confirm_and_complete(client, app):
    seller, item_id, response = _create_order(client, app)
    order_id = response.request.path.rsplit("/", 1)[-1]

    login(client, "seller")
    response = client.post("/orders/%s/action" % order_id, data={"action": "confirm"},
                           follow_redirects=True)
    assert "已确认".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "confirmed"

    login(client, "buyer")
    response = client.post("/orders/%s/action" % order_id, data={"action": "complete"},
                           follow_redirects=True)
    assert "已完成".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "completed"
    with app.app_context():
        assert get_db().execute("SELECT status FROM item WHERE id = ?", (item_id,)).fetchone()[0] \
            == "sold"


def test_illegal_transition_blocked(client, app):
    seller, item_id, response = _create_order(client, app)
    order_id = response.request.path.rsplit("/", 1)[-1]

    # pending 不能直接 complete
    login(client, "buyer")
    response = client.post("/orders/%s/action" % order_id, data={"action": "complete"},
                           follow_redirects=True)
    assert "不能执行该操作".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "pending"


def test_buyer_cannot_confirm(client, app):
    seller, item_id, response = _create_order(client, app)
    order_id = response.request.path.rsplit("/", 1)[-1]

    response = client.post("/orders/%s/action" % order_id, data={"action": "confirm"},
                           follow_redirects=True)
    assert "没有权限".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "pending"


def test_cancelled_order_is_terminal(client, app):
    seller, item_id, response = _create_order(client, app)
    order_id = response.request.path.rsplit("/", 1)[-1]

    response = client.post("/orders/%s/action" % order_id, data={"action": "cancel"},
                           follow_redirects=True)
    assert "已取消".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "cancelled"

    login(client, "seller")
    response = client.post("/orders/%s/action" % order_id, data={"action": "confirm"},
                           follow_redirects=True)
    assert "不能执行该操作".encode("utf-8") in response.data
    assert _order_status(app, order_id) == "cancelled"


def test_outsider_cannot_view_order(client, app):
    seller, item_id, response = _create_order(client, app)
    order_id = response.request.path.rsplit("/", 1)[-1]

    add_user(app, "outsider")
    login(client, "outsider")
    assert client.get("/orders/%s" % order_id).status_code == 404


def test_order_lists_for_both_sides(client, app):
    seller, item_id, response = _create_order(client, app)
    assert "要下单的键盘".encode("utf-8") in client.get("/orders").data
    login(client, "seller")
    assert "要下单的键盘".encode("utf-8") in client.get("/orders").data
