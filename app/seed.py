"""演示数据：flask --app run seed-demo。生成账号、商品、收藏、留言和一个已完成订单。"""
import os
import random

import click
from flask import current_app
from flask.cli import with_appcontext
from PIL import Image, ImageDraw
from werkzeug.security import generate_password_hash

from .db import get_db, now

USERS = [
    ("admin", "管理员", "admin123456", "admin"),
    ("gaoyuanlin", "高元淋", "123456", "user"),
    ("lisi", "李思", "123456", "user"),
    ("wangwu", "王武", "123456", "user"),
]

ITEMS = [
    ("高等数学 第七版 上下册", "图书教材", "轻微使用", 25, "大一用过的教材，无笔记，含两本。", "approved"),
    ("罗技 M330 静音鼠标", "电子数码", "几乎全新", 59, "买重了，仅拆封试用，配件齐全。", "approved"),
    ("宿舍小台灯（USB 供电）", "生活用品", "轻微使用", 18, "三档亮度，可夹床头，毕业带不走。", "approved"),
    ("篮球 斯伯丁 7 号", "运动器材", "明显使用", 45, "室外场打过一学期，气足。", "approved"),
    ("英语四级真题 2024—2025", "图书教材", "全新", 15, "买多了一套，全新未拆。", "approved"),
    ("优衣库 卫衣 M 码", "服饰鞋包", "几乎全新", 40, "穿过两次，洗过一次，无瑕疵。", "approved"),
    ("机械键盘 87 键 青轴", "电子数码", "轻微使用", 88, "手感好，宿舍太吵所以出。", "pending"),
    ("插线板 6 位 3 米", "生活用品", "几乎全新", 12, "换宿舍多买的，全新。", "pending"),
]

COLORS = [(214, 226, 240), (232, 224, 210), (214, 232, 214), (240, 224, 224),
          (228, 220, 240), (222, 236, 240), (238, 230, 214), (226, 226, 232)]


def _make_image(stem, label, color):
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    img = Image.new("RGB", (900, 675), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 880, 655], outline=(120, 120, 120), width=3)
    draw.text((40, 600), label.encode("utf-8", "ignore").decode("utf-8", "ignore"),
              fill=(60, 60, 60))
    img.save(os.path.join(upload_dir, "%s.jpg" % stem), "JPEG", quality=88)
    thumb = img.copy()
    thumb.thumbnail((480, 480))
    thumb.save(os.path.join(upload_dir, "%s_thumb.jpg" % stem), "JPEG", quality=82)
    return "uploads/%s.jpg" % stem, "uploads/%s_thumb.jpg" % stem


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    """写入演示数据（重复执行会先清空业务表）。"""
    conn = get_db()
    conn.execute("DELETE FROM message")
    conn.execute("DELETE FROM favorite")
    conn.execute("DELETE FROM trade_order")
    conn.execute("DELETE FROM item")
    conn.execute("DELETE FROM user")
    conn.commit()

    user_ids = {}
    for username, nickname, password, role in USERS:
        cur = conn.execute(
            "INSERT INTO user (username, nickname, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (username, nickname, generate_password_hash(password), role, now()),
        )
        user_ids[username] = cur.lastrowid

    seller = user_ids["gaoyuanlin"]
    random.seed(20261115)
    item_ids = []
    for index, (title, category, condition, price, desc, status) in enumerate(ITEMS):
        stem = "demo%02d" % (index + 1)
        image, thumb = _make_image(stem, title, COLORS[index % len(COLORS)])
        cur = conn.execute(
            "INSERT INTO item (title, description, price, category, condition, image, thumb,"
            " status, seller_id, review_note, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, desc, price, category, condition, image, thumb, status, seller,
             "审核通过（管理员）" if status == "approved" else None, now(), now()),
        )
        item_ids.append(cur.lastrowid)

    buyer = user_ids["lisi"]
    conn.execute(
        "INSERT INTO favorite (user_id, item_id, created_at) VALUES (?, ?, ?)",
        (buyer, item_ids[1], now()),
    )
    conn.execute(
        "INSERT INTO favorite (user_id, item_id, created_at) VALUES (?, ?, ?)",
        (buyer, item_ids[3], now()),
    )
    message_cur = conn.execute(
        "INSERT INTO message (item_id, user_id, parent_id, content, created_at)"
        " VALUES (?, ?, NULL, ?, ?)",
        (item_ids[0], buyer, "教材还在吗？有笔记吗？", now()),
    )
    conn.execute(
        "INSERT INTO message (item_id, user_id, parent_id, content, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (item_ids[0], seller, message_cur.lastrowid, "在的，基本无笔记，可以当面看。", now()),
    )
    order_cur = conn.execute(
        "INSERT INTO trade_order (item_id, buyer_id, seller_id, status, created_at, updated_at)"
        " VALUES (?, ?, ?, 'completed', ?, ?)",
        (item_ids[3], buyer, seller, now(), now()),
    )
    conn.execute("UPDATE item SET status = 'sold' WHERE id = ?", (item_ids[3],))
    conn.commit()
    click.echo("演示数据写入完成：用户 %d 个、商品 %d 件、订单 %d 个"
               % (len(user_ids), len(item_ids), order_cur.lastrowid))


def init_app(app):
    app.cli.add_command(seed_demo_command)
