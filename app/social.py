"""收藏与留言：收藏可切换，留言支持卖家回复（parent_id 指向被回复的留言）。"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db, now
from .items import get_item

bp = Blueprint("social", __name__)


@bp.route("/items/<int:item_id>/favorite", methods=("POST",))
@login_required
def favorite(item_id):
    item = get_item(item_id)
    if item is None or item["status"] not in ("approved", "sold"):
        flash("商品不存在或已下架", "error")
        return redirect(url_for("items.index"))

    conn = get_db()
    exists = conn.execute(
        "SELECT 1 FROM favorite WHERE user_id = ? AND item_id = ?",
        (g.user["id"], item_id),
    ).fetchone()
    if exists:
        conn.execute(
            "DELETE FROM favorite WHERE user_id = ? AND item_id = ?", (g.user["id"], item_id)
        )
        flash("已取消收藏", "success")
    else:
        conn.execute(
            "INSERT INTO favorite (user_id, item_id, created_at) VALUES (?, ?, ?)",
            (g.user["id"], item_id, now()),
        )
        flash("已收藏", "success")
    conn.commit()
    return redirect(url_for("items.detail", item_id=item_id))


@bp.route("/favorites")
@login_required
def favorites():
    rows = get_db().execute(
        "SELECT i.*, f.created_at AS fav_at FROM favorite f JOIN item i ON i.id = f.item_id"
        " WHERE f.user_id = ? ORDER BY f.created_at DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("social/favorites.html", items=rows)


@bp.route("/items/<int:item_id>/messages", methods=("POST",))
@login_required
def add_message(item_id):
    item = get_item(item_id)
    if item is None or item["status"] not in ("approved", "sold"):
        flash("商品不存在或已下架，不能留言", "error")
        return redirect(url_for("items.index"))

    content = request.form.get("content", "").strip()
    parent_id = request.form.get("parent_id", type=int)
    error = None
    if not content:
        error = "留言不能为空"
    elif len(content) > 300:
        error = "留言不超过 300 字"

    conn = get_db()
    if error is None and parent_id is not None:
        parent = conn.execute(
            "SELECT * FROM message WHERE id = ? AND item_id = ?", (parent_id, item_id)
        ).fetchone()
        if parent is None:
            error = "被回复的留言不存在"
        elif item["seller_id"] != g.user["id"]:
            error = "只有发布者可以回复留言"
        elif parent["user_id"] == g.user["id"]:
            error = "不能回复自己的留言"

    if error is not None:
        flash(error, "error")
    else:
        conn.execute(
            "INSERT INTO message (item_id, user_id, parent_id, content, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (item_id, g.user["id"], parent_id, content, now()),
        )
        conn.commit()
        flash("回复成功" if parent_id else "留言成功", "success")
    return redirect(url_for("items.detail", item_id=item_id))
