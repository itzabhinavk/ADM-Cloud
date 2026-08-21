import io
import os
import sys

import pytest
from PIL import Image as PILImage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import User, UserRole  # noqa: E402


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


def make_user(email="user@example.com", password="Password123", **kwargs):
    user = User(
        email=email,
        role=kwargs.get("role", UserRole.USER),
        email_verified=kwargs.get("email_verified", True),
        is_blocked=kwargs.get("is_blocked", False),
    )
    user.set_password(password)
    _db.session.add(user)
    _db.session.commit()
    return user


def login(client, email="user@example.com", password="Password123"):
    return client.post(
        "/auth/login", data={"email": email, "password": password}, follow_redirects=False
    )


def make_image_bytes(fmt="PNG", size=(24, 24)):
    buffer = io.BytesIO()
    PILImage.new("RGB", size, (120, 90, 200)).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def fake_storage(monkeypatch):
    """Mock the storage provider; no network calls in tests."""
    from app.services import storage_service

    state = {"uploads": [], "deleted": []}

    def _upload(data, filename):
        public_id = f"test/{filename}"
        state["uploads"].append(public_id)
        return {
            "public_id": public_id,
            "url": f"http://cdn.test/upload/{filename}",
            "secure_url": f"https://cdn.test/upload/{filename}",
            "width": 24,
            "height": 24,
            "bytes": len(data),
        }

    def _delete(public_id):
        state["deleted"].append(public_id)
        return True

    monkeypatch.setattr(storage_service, "upload_image", _upload)
    monkeypatch.setattr(storage_service, "delete_image", _delete)
    from app.services import image_service

    monkeypatch.setattr(image_service.storage_service, "upload_image", _upload)
    monkeypatch.setattr(image_service.storage_service, "delete_image", _delete)
    return state
