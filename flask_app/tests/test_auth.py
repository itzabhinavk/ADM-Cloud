from app.extensions import db
from app.models import EmailToken, User

from .conftest import login, make_user


def test_registration_creates_unverified_user(client, app):
    res = client.post(
        "/auth/register",
        data={"email": "New@Example.com", "password": "Password123", "confirm_password": "Password123"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    user = User.query.filter_by(email="new@example.com").first()
    assert user is not None
    assert user.email_verified is False
    assert user.role == "user"
    assert EmailToken.query.filter_by(user_id=user.id).count() == 1


def test_registration_does_not_reveal_existing_account(client, app):
    make_user(email="taken@example.com")
    res = client.post(
        "/auth/register",
        data={"email": "taken@example.com", "password": "Password123", "confirm_password": "Password123"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"already" not in res.data.lower()
    assert User.query.filter_by(email="taken@example.com").count() == 1


def test_password_is_hashed(app):
    user = make_user(email="hash@example.com", password="Password123")
    assert user.password_hash != "Password123"
    assert user.check_password("Password123")
    assert not user.check_password("wrong-password")


def test_role_cannot_be_set_via_registration(client, app):
    client.post(
        "/auth/register",
        data={"email": "sneaky@example.com", "password": "Password123",
              "confirm_password": "Password123", "role": "admin"},
        follow_redirects=True,
    )
    assert User.query.filter_by(email="sneaky@example.com").first().role == "user"


def test_login_and_logout(client, app):
    make_user(email="login@example.com")
    res = login(client, "login@example.com")
    assert res.status_code == 302
    assert client.get("/dashboard").status_code == 200
    client.post("/auth/logout")
    assert client.get("/dashboard").status_code == 302


def test_login_updates_last_login(client, app):
    user = make_user(email="stamp@example.com")
    assert user.last_login_at is None
    login(client, "stamp@example.com")
    assert db.session.get(User, user.id).last_login_at is not None


def test_bad_password_rejected(client, app):
    make_user(email="bad@example.com")
    res = client.post("/auth/login", data={"email": "bad@example.com", "password": "nope12345678"})
    assert res.status_code == 401


def test_blocked_user_cannot_authenticate(client, app):
    make_user(email="blocked@example.com", is_blocked=True)
    res = client.post("/auth/login", data={"email": "blocked@example.com", "password": "Password123"})
    assert res.status_code == 403
    assert client.get("/dashboard").status_code == 302


def test_email_verification_flow(client, app):
    from app.services.tokens import issue_token

    user = make_user(email="verify@example.com", email_verified=False)
    token = issue_token(user)
    assert client.get(f"/auth/verify/{token}").status_code == 200
    assert db.session.get(User, user.id).email_verified is True
    # single use
    assert client.get(f"/auth/verify/{token}").status_code == 400


def test_expired_verification_token_rejected(client, app):
    from datetime import datetime, timedelta, timezone

    from app.services.tokens import issue_token

    user = make_user(email="expired@example.com", email_verified=False)
    token = issue_token(user)
    record = EmailToken.query.filter_by(user_id=user.id).first()
    record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.session.commit()
    assert client.get(f"/auth/verify/{token}").status_code == 400
    assert db.session.get(User, user.id).email_verified is False


def test_unverified_user_cannot_reach_dashboard(client, app):
    make_user(email="pending@example.com", email_verified=False)
    login(client, "pending@example.com")
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/auth/verify-email" in res.headers["Location"]


def test_anonymous_dashboard_redirects_to_login(client, app):
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]


def test_account_can_be_deleted(client, app, fake_storage):
    user = make_user(email="delete@example.com")
    login(client, "delete@example.com")
    res = client.post("/auth/account/delete", follow_redirects=False)
    assert res.status_code == 302
    assert User.query.get(user.id) is None
    assert client.get("/dashboard").status_code == 302
