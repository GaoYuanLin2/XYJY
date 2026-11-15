"""后台：商品审核（通过/驳回）、下架、数据概览。"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import admin_required
from .db import get_db, now
from .items import ITEM_STATUS, get_item
from .orders import STATUS_LABELS as ORDER_STATUS_LABELS

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    conn = get_db()
    stats = {
        "pending": conn.execute("SELECT COUNT(*) FROM item WHERE status = 'pending'").fetchone()[0],
        "approved": conn.execute(
            "SELECT COUNT(*) FROM item WHERE status = 'approved'"
        ).fetchone()[0],
        "users": conn.execute("SELECT COUNT(*) FROM user").fetchone()[0],
        "orders": conn.execute(
            "SELECT COUNT(*) FROM trade_order WHERE status IN ('pending', 'confirmed')"
        ).fetchone()[0],
    }
    pending_items = conn.execute(
        "SELECT i.*, u.nickname AS seller_name FROM item i JOIN user u ON u.id = i.seller_id"
        " WHERE i.status = 'pending' ORDER BY i.created_at, i.id"
    ).fetchall()
    orders = conn.execute(
        "SELECT o.*, i.title AS item_title FROM trade_order o JOIN item i ON i.id = o.item_id"
        " ORDER BY o.updated_at DESC, o.id DESC LIMIT 8"
    ).fetchall()
    return render_template(
        "admin/index.html",
        stats=stats,
        pending_items=pending_items,
        orders=orders,
        status_labels=ITEM_STATUS,
        order_status_labels=ORDER_STATUS_LABELS,
    )


@bp.route("/items")
@admin_required
def items():
    status = request.args.get("status", "")
    clauses, params = [], []
    if status in ITEM_STATUS:
        clauses.append("status = ?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = get_db().execute(
        "SELECT i.*, u.nickname AS seller_name FROM item i JOIN user u ON u.id = i.seller_id"
        + where + " ORDER BY i.created_at DESC, i.id DESC",
        params,
    ).fetchall()
    return render_template(
        "admin/items.html",
        items=rows,
        status=status,
        status_labels=ITEM_STATUS,
    )


@bp.route("/items/<int:item_id>/approve", methods=("POST",))
@admin_required
def approve(item_id):
    item = get_item(item_id)
    if item is None:
        return render_template("404.html"), 404
    if item["status"] != "pending":
        flash("只有待审核的商品可以审核", "warning")
        return redirect(request.referrer or url_for("admin.index"))
    conn = get_db()
    conn.execute(
        "UPDATE item SET status = 'approved', review_note = ?, updated_at = ? WHERE id = ?",
        ("审核通过（%s）" % g.user["nickname"], now(), item_id),
    )
    conn.commit()
    flash("已通过审核：%s" % item["title"], "success")
    return redirect(request.referrer or url_for("admin.index"))


@bp.route("/items/<int:item_id>/reject", methods=("POST",))
@admin_required
def reject(item_id):
    item = get_item(item_id)
    if item is None:
        return render_template("404.html"), 404
    if item["status"] != "pending":
        flash("只有待审核的商品可以审核", "warning")
        return redirect(request.referrer or url_for("admin.index"))
    note = request.form.get("note", "").strip()
    if not note:
        flash("驳回必须填写原因", "error")
        return redirect(request.referrer or url_for("admin.index"))
    conn = get_db()
    conn.execute(
        "UPDATE item SET status = 'rejected', review_note = ?, updated_at = ? WHERE id = ?",
        (note, now(), item_id),
    )
    conn.commit()
    flash("已驳回：%s" % item["title"], "success")
    return redirect(request.referrer or url_for("admin.index"))


@bp.route("/items/<int:item_id>/offline", methods=("POST",))
@admin_required
def offline(item_id):
    item = get_item(item_id)
    if item is None:
        return render_template("404.html"), 404
    conn = get_db()
    conn.execute(
        "UPDATE item SET status = 'offline', updated_at = ? WHERE id = ?",
        (now(), item_id),
    )
    conn.commit()
    flash("已下架：%s" % item["title"], "success")
    return redirect(request.referrer or url_for("admin.items"))
