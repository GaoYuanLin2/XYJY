"""测试辅助函数：建用户、建商品、登录。"""
import io

from PIL import Image
from werkzeug.security import generate_password_hash

from app.db import get_db, now


def add_user(app, username="stu1", nickname=None, password="pass1234", role="user"):
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO user (username, nickname, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (username, nickname or username, generate_password_hash(password), role, now()),
        )
        conn.commit()
        return cur.lastrowid


def add_item(app, seller_id, status="approved", title="二手教材", price=20.0,
             category="图书教材", condition="轻微使用", description="测试商品"):
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO item (title, description, price, category, condition, image, thumb,"
            " status, seller_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?)",
            (title, description, price, category, condition, status, seller_id, now(), now()),
        )
        conn.commit()
        return cur.lastrowid


def login(client, username="stu1", password="pass1234"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def png_bytes(size=(64, 48), color=(120, 160, 200)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def item_form(overrides=None):
    data = {
        "title": "宿舍小台灯",
        "price": "18.5",
        "category": "生活用品",
        "condition": "轻微使用",
        "description": "三档亮度，可夹床头。",
    }
    if overrides:
        data.update(overrides)
    return data
