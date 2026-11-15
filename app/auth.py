"""登录、注册、退出。密码用 pbkdf2 加盐存储，session 只存 user_id。"""
import functools
import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, now

bp = Blueprint("auth", __name__)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            flash("需要管理员权限", "error")
            return redirect(url_for("items.index"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        error = None
        if not USERNAME_RE.match(username):
            error = "用户名需为 3—20 位字母、数字或下划线"
        elif not nickname or len(nickname) > 20:
            error = "昵称不能为空且不超过 20 字"
        elif len(password) < 6:
            error = "密码至少 6 位"
        elif password != password2:
            error = "两次输入的密码不一致"
        elif get_db().execute("SELECT 1 FROM user WHERE username = ?", (username,)).fetchone():
            error = "用户名已被注册"

        if error is None:
            conn = get_db()
            conn.execute(
                "INSERT INTO user (username, nickname, password_hash, role, created_at)"
                " VALUES (?, ?, ?, 'user', ?)",
                (username, nickname, generate_password_hash(password), now()),
            )
            conn.commit()
            flash("注册成功，请登录", "success")
            return redirect(url_for("auth.login"))
        flash(error, "error")
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("用户名或密码不正确", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("欢迎回来，%s" % user["nickname"], "success")
            return redirect(url_for("items.index"))
    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("已退出登录", "success")
    return redirect(url_for("items.index"))
