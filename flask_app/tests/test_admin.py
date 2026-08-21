import io

from app.extensions import db
from app.models import Image, User, UserRole

from .conftest import login, make_image_bytes, make_user


def test_normal_user_cannot_access_admin(client, app):
    make_user()
    login(client)
    assert client.get("/admin/").status_code == 403
    assert client.get("/admin/users").status_code == 403
    assert client.get("/api/admin/users").status_code == 403


def test_anonymous_admin_access_denied(client, app):
    assert client.get("/api/admin/users").status_code == 401


def test_admin_can_view_and_block(client, app):
    make_user(email="admin@example.com", role=UserRole.ADMIN)
    victim = make_user(email="victim@example.com")
    login(client, "admin@example.com")

    assert client.get("/admin/").status_code == 200
    assert client.post(f"/api/admin/users/{victim.id}/block").status_code == 200
    assert db.session.get(User, victim.id).is_blocked is True
    assert client.post(f"/api/admin/users/{victim.id}/unblock").status_code == 200
    assert db.session.get(User, victim.id).is_blocked is False


def test_last_admin_cannot_be_deleted(client, app):
    admin = make_user(email="solo@example.com", role=UserRole.ADMIN)
    other = make_user(email="second@example.com", role=UserRole.ADMIN)
    login(client, "solo@example.com")

    # deleting the other admin is allowed while two remain
    assert client.delete(f"/api/admin/users/{other.id}").status_code == 200
    # an admin cannot remove themselves
    assert client.delete(f"/api/admin/users/{admin.id}").status_code == 400
    assert db.session.get(User, admin.id) is not None


def test_deleting_user_removes_images_and_assets(client, app, fake_storage):
    make_user(email="admin@example.com", role=UserRole.ADMIN)
    owner = make_user(email="owner@example.com")
    login(client, "owner@example.com")
    client.post(
        "/api/images/upload",
        data={"file": (io.BytesIO(make_image_bytes()), "a.png")},
        content_type="multipart/form-data",
    )
    client.post("/auth/logout")

    login(client, "admin@example.com")
    assert client.delete(f"/api/admin/users/{owner.id}").status_code == 200
    assert Image.query.count() == 0
    assert db.session.get(User, owner.id) is None
    assert fake_storage["deleted"]
