"""校园二手交易平台（先跑再说 · 校园集市）应用工厂。"""
import os

from flask import Flask, render_template

from . import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-please-change",
        DATABASE=os.path.join(app.instance_path, "xyjy.sqlite"),
        UPLOAD_FOLDER=os.path.join(app.static_folder, "uploads"),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
        PER_PAGE=6,
        ALLOWED_IMAGE_EXT={"png", "jpg", "jpeg", "webp"},
    )
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, "uploads"), exist_ok=True)

    db.init_app(app)

    from . import auth, items

    app.register_blueprint(auth.bp)
    app.register_blueprint(items.bp)

    @app.context_processor
    def inject_globals():
        return {
            "categories": items.CATEGORIES,
            "conditions": items.CONDITIONS,
            "sort_choices": items.SORT_CHOICES,
        }

    @app.template_filter("yuan")
    def yuan(value):
        return "¥%.2f" % float(value)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    return app
