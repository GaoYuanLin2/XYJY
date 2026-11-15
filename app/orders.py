"""订单：状态机 待确认→已确认→已完成/已取消，非法跳转一律拦截。"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db, now
from .items import get_item

bp = Blueprint("orders", __name__)

STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "completed": "已完成",
    "cancelled": "已取消",
}
# 状态机白名单：当前状态 -> {动作: 下一状态}
TRANSITIONS = {
    "pending": {"confirm": "confirmed", "cancel": "cancelled"},
    "confirmed": {"complete": "completed", "cancel": "cancelled"},
    "completed": {},
    "cancelled": {},
}
ACTION_LABELS = {"confirm": "卖家确认", "complete": "买家确认收货", "cancel": "取消订单"}
# 动作 -> 谁可以执行
ACTION_ROLE = {"confirm": "seller", "complete": "buyer", "cancel": "both"}


def get_order(order_id):
    return get_db().execute(
        "SELECT o.*, i.title AS item_title, i.price AS item_price, i.thumb AS item_thumb,"
        " b.nickname AS buyer_nickname, s.nickname AS seller_nickname"
        " FROM trade_order o JOIN item i ON i.id = o.item_id"
        " JOIN user b ON b.id = o.buyer_id JOIN user s ON s.id = o.seller_id"
        " WHERE o.id = ?",
        (order_id,),
    ).fetchone()


def allowed_actions(order, user):
    """返回当前用户在该订单上可执行的动作列表。"""
    actions = []
    for action, target in TRANSITIONS.get(order["status"], {}).items():
        role = ACTION_ROLE[action]
        if role == "both" or (role == "buyer" and user["id"] == order["buyer_id"]) or (
            role == "seller" and user["id"] == order["seller_id"]
        ):
            actions.append((action, target))
    return actions


@bp.route("/items/<int:item_id>/order", methods=("POST",))
@login_required
def create(item_id):
    item = get_item(item_id)
    if item is None or item["status"] != "approved":
        flash("商品当前不可下单", "error")
        return redirect(url_for("items.index"))
    if item["seller_id"] == g.user["id"]:
        flash("不能购买自己发布的商品", "error")
        return redirect(url_for("items.detail", item_id=item_id))

    conn = get_db()
    active = conn.execute(
        "SELECT 1 FROM trade_order WHERE item_id = ? AND status IN ('pending', 'confirmed')",
        (item_id,),
    ).fetchone()
    if active:
        flash("该商品已有进行中的订单", "warning")
        return redirect(url_for("items.detail", item_id=item_id))

    cur = conn.execute(
        "INSERT INTO trade_order (item_id, buyer_id, seller_id, status, created_at, updated_at)"
        " VALUES (?, ?, ?, 'pending', ?, ?)",
        (item_id, g.user["id"], item["seller_id"], now(), now()),
    )
    conn.commit()
    flash("已下单，等待卖家确认", "success")
    return redirect(url_for("orders.detail", order_id=cur.lastrowid))


@bp.route("/orders")
@login_required
def index():
    conn = get_db()
    purchases = conn.execute(
        "SELECT o.*, i.title AS item_title, i.price AS item_price, i.thumb AS item_thumb"
        " FROM trade_order o JOIN item i ON i.id = o.item_id"
        " WHERE o.buyer_id = ? ORDER BY o.created_at DESC, o.id DESC",
        (g.user["id"],),
    ).fetchall()
    sales = conn.execute(
        "SELECT o.*, i.title AS item_title, i.price AS item_price, i.thumb AS item_thumb"
        " FROM trade_order o JOIN item i ON i.id = o.item_id"
        " WHERE o.seller_id = ? ORDER BY o.created_at DESC, o.id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "orders/list.html",
        purchases=purchases,
        sales=sales,
        status_labels=STATUS_LABELS,
    )


@bp.route("/orders/<int:order_id>")
@login_required
def detail(order_id):
    order = get_order(order_id)
    if order is None or g.user["id"] not in (order["buyer_id"], order["seller_id"]):
        return render_template("404.html"), 404
    return render_template(
        "orders/detail.html",
        order=order,
        actions=allowed_actions(order, g.user),
        action_labels=ACTION_LABELS,
        status_labels=STATUS_LABELS,
    )


@bp.route("/orders/<int:order_id>/action", methods=("POST",))
@login_required
def action(order_id):
    order = get_order(order_id)
    if order is None or g.user["id"] not in (order["buyer_id"], order["seller_id"]):
        return render_template("404.html"), 404

    name = request.form.get("action", "")
    target = TRANSITIONS.get(order["status"], {}).get(name)
    if target is None:
        flash("当前状态不能执行该操作", "error")
        return redirect(url_for("orders.detail", order_id=order_id))

    role = ACTION_ROLE[name]
    permitted = (
        role == "both"
        or (role == "buyer" and g.user["id"] == order["buyer_id"])
        or (role == "seller" and g.user["id"] == order["seller_id"])
    )
    if not permitted:
        flash("你没有权限执行该操作", "error")
        return redirect(url_for("orders.detail", order_id=order_id))

    conn = get_db()
    conn.execute(
        "UPDATE trade_order SET status = ?, updated_at = ? WHERE id = ?",
        (target, now(), order_id),
    )
    if target == "completed":
        conn.execute(
            "UPDATE item SET status = 'sold', updated_at = ? WHERE id = ?",
            (now(), order["item_id"]),
        )
    elif target == "cancelled":
        conn.execute(
            "UPDATE item SET status = 'approved', updated_at = ? WHERE id = ? AND status = 'sold'",
            (now(), order["item_id"]),
        )
    conn.commit()
    flash("订单状态已更新为「%s」" % STATUS_LABELS[target], "success")
    return redirect(url_for("orders.detail", order_id=order_id))
