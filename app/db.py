"""数据库连接与初始化。"""
import sqlite3
from datetime import datetime

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = get_db()
    with current_app.open_resource("schema.sql") as schema:
        conn.executescript(schema.read().decode("utf-8"))
    conn.commit()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@click.command("init-db")
@with_appcontext
def init_db_command():
    """建表（空库初始化）。"""
    init_db()
    click.echo("数据库初始化完成")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
