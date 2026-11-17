import io
import re

import pytest

from app import create_app
from app.extensions import db
from app.seed import seed_all

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
NEW_PASSWORD = "Fresh-Passw0rd-2026"


def make_app(tmp_path, **overrides):
    config = {"TESTING": True, "DATA_DIR": str(tmp_path), "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False}
    config.update(overrides)
    app = create_app(config)
    with app.app_context():
        db.create_all()
        app.config["ADMIN_TEMP_PASSWORD"] = seed_all()
    return app


@pytest.fixture
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(app):
    """A client signed in as admin with the forced password change already done."""
    c = app.test_client()
    c.post("/admin/login", data={"username": "admin", "password": app.config["ADMIN_TEMP_PASSWORD"]})
    c.post("/admin/change-password", data={"current": app.config["ADMIN_TEMP_PASSWORD"], "new": NEW_PASSWORD, "confirm": NEW_PASSWORD})
    return c


def captcha_answer(client, page, key):
    """Load the page that renders the form, then read the expected answer from the session."""
    client.get(page)
    with client.session_transaction() as sess:
        return sess[f"captcha_{key}"]


def contact(**extra):
    data = {"name": "Asha Verma", "phone": "+91 98765 43210", "email": "asha@example.com", "consent": "1"}
    data.update(extra)
    return data


def upload(data, name):
    return (io.BytesIO(data), name)
