"""页面冒烟测试与演示数据命令。"""
from app.db import get_db


def test_index_renders_for_guest(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "校园集市".encode("utf-8") in response.data


def test_unknown_item_returns_404(client):
    assert client.get("/items/999").status_code == 404
    assert "不存在".encode("utf-8") in client.get("/items/999").data


def test_unknown_path_returns_404(client):
    assert client.get("/no-such-page").status_code == 404


def test_seed_demo_command(client, app):
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code == 0
    assert "演示数据写入完成" in result.output

    with app.app_context():
        stats = {
            "users": get_db().execute("SELECT COUNT(*) FROM user").fetchone()[0],
            "items": get_db().execute("SELECT COUNT(*) FROM item").fetchone()[0],
            "approved": get_db().execute(
                "SELECT COUNT(*) FROM item WHERE status = 'approved'").fetchone()[0],
            "sold": get_db().execute(
                "SELECT COUNT(*) FROM item WHERE status = 'sold'").fetchone()[0],
            "orders": get_db().execute("SELECT COUNT(*) FROM trade_order").fetchone()[0],
        }
    # 6 件在售商品里有 1 件已走完订单变 sold，另 2 件待审核
    assert stats == {"users": 4, "items": 8, "approved": 5, "sold": 1, "orders": 1}

    # 每页 3 件，首页是最新发布的 3 件在售商品
    response = client.get("/")
    assert response.status_code == 200
    assert "优衣库".encode("utf-8") in response.data
    assert "机械键盘".encode("utf-8") not in response.data  # 待审核不展示


def test_seed_demo_is_idempotent(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM item").fetchone()[0] == 8
