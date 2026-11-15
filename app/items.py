"""商品：发布（含图片）、分类与成色筛选、关键词搜索、详情、下架。"""
import base64
import io
import os
import secrets

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, url_for)
from PIL import Image

from .auth import admin_required, login_required
from .db import get_db, now

bp = Blueprint("items", __name__)

CATEGORIES = ["图书教材", "电子数码", "生活用品", "服饰鞋包", "运动器材", "其他"]
CONDITIONS = ["全新", "几乎全新", "轻微使用", "明显使用"]
SORT_CHOICES = [("new", "最新发布"), ("price_asc", "价格从低到高"), ("price_desc", "价格从高到低")]
ITEM_STATUS = {
    "pending": "待审核",
    "approved": "在售",
    "rejected": "未通过",
    "offline": "已下架",
    "sold": "已售出",
}
MAX_ORIGIN = (1600, 1600)
THUMB_SIZE = (480, 480)


def parse_price(raw):
    """价格必须是 0 以上的数字，最多两位小数。"""
    try:
        value = round(float(raw), 2)
    except (TypeError, ValueError):
        return None, "价格要填数字"
    if value <= 0:
        return None, "价格必须大于 0"
    if value > 100000:
        return None, "价格不能超过 100000 元"
    return value, None


def save_image(file_storage):
    """保存原图并生成缩略图：列表页只用缩略图，详情页才加载原图。"""
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    allowed = current_app.config["ALLOWED_IMAGE_EXT"]
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise ValueError("图片只支持 png、jpg、jpeg、webp")
    raw = file_storage.read()
    if not raw:
        raise ValueError("图片内容为空")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_ORIGIN)
            stem = secrets.token_hex(8)
            origin = img.copy()
            origin.save(os.path.join(upload_dir, "%s.jpg" % stem), "JPEG", quality=88)
            thumb = img.copy()
            thumb.thumbnail(THUMB_SIZE)
            thumb.save(os.path.join(upload_dir, "%s_thumb.jpg" % stem), "JPEG", quality=82)
    except OSError as exc:
        raise ValueError("图片无法识别，请换一张") from exc
    return "uploads/%s.jpg" % stem, "uploads/%s_thumb.jpg" % stem


def encode_cursor(value, item_id):
    raw = ("%s|%s" % (value, item_id)).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token):
    if not token:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        value, item_id = raw.rsplit("|", 1)
        return value, int(item_id)
    except (ValueError, UnicodeDecodeError):
        return None


def query_items(keyword="", category="", condition="", sort="new", cursor=None,
                limit=None, status="approved"):
    """按条件查询商品，游标分页（同一游标翻页不会重复、不会漏项）。"""
    conn = get_db()
    limit = min(int(limit or current_app.config["PER_PAGE"]), 50)
    clauses = ["status = ?"]
    params = [status]

    if category:
        clauses.append("category = ?")
        params.append(category)
    if condition:
        clauses.append("condition = ?")
        params.append(condition)

    keyword = (keyword or "").strip()
    if keyword:
        like = "%%%s%%" % keyword
        clauses.append(
            "(title LIKE ? OR description LIKE ? OR category LIKE ? OR condition LIKE ?)"
        )
        params.extend([like, like, like, like])

    if sort == "price_asc":
        order_by, key, compare = "price ASC, id ASC", "price", ">"
    elif sort == "price_desc":
        order_by, key, compare = "price DESC, id DESC", "price", "<"
    else:
        sort = "new"
        order_by, key, compare = "created_at DESC, id DESC", "created_at", "<"

    decoded = decode_cursor(cursor)
    if decoded is not None:
        value, last_id = decoded
        if key == "price":
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None
        if value is not None:
            clauses.append("(%s %s ? OR (%s = ? AND id %s ?))" % (key, compare, key, compare))
            params.extend([value, value, last_id])

    sql = "SELECT * FROM item WHERE %s ORDER BY %s LIMIT ?" % (" AND ".join(clauses), order_by)
    rows = conn.execute(sql, params + [limit + 1]).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if has_more and rows:
        next_cursor = encode_cursor(rows[-1][key], rows[-1]["id"])
    return rows, next_cursor, sort


def get_item(item_id):
    return get_db().execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()


def can_view(item):
    if item["status"] in ("approved", "sold"):
        return True
    if g.user is None:
        return False
    return g.user["id"] == item["seller_id"] or g.user["role"] == "admin"


def read_item_form():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    condition = request.form.get("condition", "").strip()
    price, price_error = parse_price(request.form.get("price", ""))

    error = None
    if not 2 <= len(title) <= 60:
        error = "标题需在 2—60 字之间"
    elif price_error:
        error = price_error
    elif category not in CATEGORIES:
        error = "请选择商品分类"
    elif condition not in CONDITIONS:
        error = "请选择商品成色"
    elif len(description) > 500:
        error = "描述不超过 500 字"

    image = thumb = None
    if error is None:
        upload = request.files.get("image")
        if upload is not None and upload.filename:
            try:
                image, thumb = save_image(upload)
            except ValueError as exc:
                error = str(exc)

    values = {
        "title": title,
        "description": description,
        "category": category,
        "condition": condition,
        "price": price,
        "image": image,
        "thumb": thumb,
    }
    return values, error


@bp.route("/")
def index():
    keyword = request.args.get("q", "")
    category = request.args.get("category", "")
    condition = request.args.get("condition", "")
    sort = request.args.get("sort", "new")
    cursor = request.args.get("cursor", "")
    if category and category not in CATEGORIES:
        category = ""
    if condition and condition not in CONDITIONS:
        condition = ""

    items, next_cursor, sort = query_items(keyword, category, condition, sort, cursor)
    return render_template(
        "items/list.html",
        items=items,
        next_cursor=next_cursor,
        keyword=keyword,
        category=category,
        condition=condition,
        sort=sort,
    )


@bp.route("/items/<int:item_id>")
def detail(item_id):
    item = get_item(item_id)
    if item is None or not can_view(item):
        return render_template("404.html"), 404

    conn = get_db()
    favorite = False
    active_order = None
    if g.user is not None:
        favorite = conn.execute(
            "SELECT 1 FROM favorite WHERE user_id = ? AND item_id = ?",
            (g.user["id"], item_id),
        ).fetchone() is not None

    active_order = conn.execute(
        "SELECT * FROM trade_order WHERE item_id = ? AND status IN ('pending', 'confirmed')",
        (item_id,),
    ).fetchone()

    messages = conn.execute(
        "SELECT m.*, u.nickname FROM message m JOIN user u ON u.id = m.user_id"
        " WHERE m.item_id = ? ORDER BY m.created_at, m.id",
        (item_id,),
    ).fetchall()

    return render_template(
        "items/detail.html",
        item=item,
        favorite=favorite,
        active_order=active_order,
        messages=messages,
        status_labels=ITEM_STATUS,
    )


@bp.route("/items/new", methods=("GET", "POST"))
@login_required
def new():
    if request.method == "POST":
        values, error = read_item_form()
        if error is None:
            conn = get_db()
            cur = conn.execute(
                "INSERT INTO item (title, description, price, category, condition, image, thumb,"
                " status, seller_id, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                (values["title"], values["description"], values["price"], values["category"],
                 values["condition"], values["image"], values["thumb"], g.user["id"], now(), now()),
            )
            conn.commit()
            flash("发布成功，管理员审核通过后即在集市展示", "success")
            return redirect(url_for("items.detail", item_id=cur.lastrowid))
        flash(error, "error")
    return render_template("items/form.html", item=None)


@bp.route("/items/<int:item_id>/edit", methods=("GET", "POST"))
@login_required
def edit(item_id):
    item = get_item(item_id)
    if item is None or item["seller_id"] != g.user["id"]:
        return render_template("404.html"), 404
    if item["status"] == "sold":
        flash("已售出的商品不能再修改", "warning")
        return redirect(url_for("items.detail", item_id=item_id))

    if request.method == "POST":
        values, error = read_item_form()
        if error is None:
            conn = get_db()
            conn.execute(
                "UPDATE item SET title = ?, description = ?, price = ?, category = ?,"
                " condition = ?,"
                " image = COALESCE(?, image), thumb = COALESCE(?, thumb),"
                " status = 'pending', updated_at = ? WHERE id = ?",
                (values["title"], values["description"], values["price"], values["category"],
                 values["condition"], values["image"], values["thumb"], now(), item_id),
            )
            conn.commit()
            flash("修改已保存，重新审核通过后再次展示", "success")
            return redirect(url_for("items.detail", item_id=item_id))
        flash(error, "error")
    return render_template("items/form.html", item=item)


@bp.route("/items/<int:item_id>/offline", methods=("POST",))
@login_required
def offline(item_id):
    item = get_item(item_id)
    if item is None:
        return render_template("404.html"), 404
    if item["seller_id"] != g.user["id"] and g.user["role"] != "admin":
        flash("只有商品发布者或管理员可以下架", "error")
        return redirect(url_for("items.detail", item_id=item_id))
    if item["status"] == "sold":
        flash("已售出商品无需下架", "warning")
        return redirect(url_for("items.detail", item_id=item_id))

    conn = get_db()
    conn.execute(
        "UPDATE item SET status = 'offline', updated_at = ? WHERE id = ?",
        (now(), item_id),
    )
    conn.commit()
    flash("商品已下架", "success")
    return redirect(url_for("items.mine"))


@bp.route("/items/mine")
@login_required
def mine():
    rows = get_db().execute(
        "SELECT * FROM item WHERE seller_id = ? ORDER BY created_at DESC, id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("items/mine.html", items=rows, status_labels=ITEM_STATUS)


@bp.route("/admin-check-placeholder")
@admin_required
def admin_placeholder():
    """占位路由：保证 admin_required 被使用，实际后台在 admin 蓝图中。"""
    return redirect(url_for("admin.index"))
