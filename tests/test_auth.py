"""需求 1：注册、登录、退出与访问控制。"""
from tests.helpers import add_user, login


def test_register_then_login(client):
    response = client.post(
        "/register",
        data={"username": "newbie", "nickname": "新同学", "password": "pass1234",
              "password2": "pass1234"},
        follow_redirects=True,
    )
    assert "注册成功".encode("utf-8") in response.data

    response = login(client, "newbie", "pass1234")
    assert "欢迎回来".encode("utf-8") in response.data
    assert "我的商品".encode("utf-8") in response.data


def test_register_duplicate_username(client):
    client.post("/register", data={"username": "dup", "nickname": "甲", "password": "pass1234",
                                   "password2": "pass1234"})
    response = client.post(
        "/register",
        data={"username": "dup", "nickname": "乙", "password": "pass1234",
              "password2": "pass1234"},
        follow_redirects=True,
    )
    assert "已被注册".encode("utf-8") in response.data


def test_register_rejects_short_password(client):
    response = client.post(
        "/register",
        data={"username": "short", "nickname": "丙", "password": "123", "password2": "123"},
        follow_redirects=True,
    )
    assert "至少 6 位".encode("utf-8") in response.data


def test_register_rejects_bad_username(client):
    response = client.post(
        "/register",
        data={"username": "a!", "nickname": "丁", "password": "pass1234",
              "password2": "pass1234"},
        follow_redirects=True,
    )
    assert "3—20".encode("utf-8") in response.data


def test_register_rejects_mismatched_password(client):
    response = client.post(
        "/register",
        data={"username": "mismatch", "nickname": "戊", "password": "pass1234",
              "password2": "pass9999"},
        follow_redirects=True,
    )
    assert "不一致".encode("utf-8") in response.data


def test_login_wrong_password(client):
    add_user(client.application, "stu1")
    response = login(client, "stu1", "wrong-pass")
    assert "不正确".encode("utf-8") in response.data


def test_logout_clears_session(client):
    add_user(client.application, "stu1")
    login(client)
    response = client.post("/logout", follow_redirects=True)
    assert "已退出登录".encode("utf-8") in response.data
    assert "登录".encode("utf-8") in response.data


def test_publish_requires_login(client):
    response = client.get("/items/new")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_password_is_hashed(client, app):
    add_user(app, "hashed", password="pass1234")
    with app.app_context():
        from app.db import get_db
        row = get_db().execute(
            "SELECT password_hash FROM user WHERE username = 'hashed'"
        ).fetchone()
    assert "pass1234" not in row["password_hash"]
    assert row["password_hash"].count("$") == 2  # 方法$盐$摘要
    from werkzeug.security import check_password_hash
    assert check_password_hash(row["password_hash"], "pass1234")
