"""pytest 夹具：每个用例一个独立的临时数据库和上传目录。"""
import os
import tempfile

import pytest

from app import create_app
from app.db import init_db


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    upload_dir = tempfile.mkdtemp(prefix="xyjy-upload-")
    application = create_app({
        "TESTING": True,
        "DATABASE": db_path,
        "UPLOAD_FOLDER": upload_dir,
        "SECRET_KEY": "test-secret",
        "PER_PAGE": 3,
    })
    with application.app_context():
        init_db()
    yield application
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()
