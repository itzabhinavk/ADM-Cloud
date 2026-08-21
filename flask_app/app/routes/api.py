"""JSON API for auth and admin operations (same session auth as the UI)."""

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, limiter
from ..models import User, UserRole
from ..routes.admin import _admin_count, _get_user_or_404
from ..services import image_service
from ..services.email_service import send_verification_email
from ..services.tokens import issue_token
from ..utils.decorators import admin_required

api_bp = Blueprint("api", __name__)


def _payload() -> dict:
    return request.get_json(silent=True) or {}


@api_bp.route("/auth/register", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_REGISTER", "5 per hour"))
def register():
    data = _payload()
    email = User.normalize_email(data.get("email"))
    password = data.get("password") or ""
    if "@" not in email or len(password) < 10:
        return jsonify({"error": "Provide a valid email and a strong password."}), 400

    if User.query.filter_by(email=email).first() is None:
        user = User(email=email, role=UserRole.USER, email_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user, issue_token(user))
    # Identical response either way: account existence is never disclosed.
    return jsonify({"message": "Check your inbox to confirm your email address."}), 202


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_LOGIN", "10 per 15 minutes"))
def login():
    data = _payload()
    user = User.query.filter_by(email=User.normalize_email(data.get("email"))).first()
    if user is None or not user.check_password(data.get("password") or ""):
        return jsonify({"error": "Those credentials are not valid."}), 401
    if user.is_blocked:
        return jsonify({"error": "This account is not available."}), 403

    login_user(user)
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Signed out."})


@api_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": current_user.to_dict(include_admin_fields=current_user.is_admin)})


@api_bp.route("/admin/users", methods=["GET"])
@admin_required
def admin_users():
    page = max(1, request.args.get("page", 1, type=int))
    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return jsonify(
        {
            "users": [u.to_dict(include_admin_fields=True) for u in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@api_bp.route("/admin/users/<int:user_id>/block", methods=["POST"])
@admin_required
def admin_block(user_id: int):
    user = _get_user_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"error": "You cannot block your own account."}), 400
    if user.is_admin and _admin_count() <= 1:
        return jsonify({"error": "At least one administrator must remain."}), 400
    user.is_blocked = True
    db.session.commit()
    return jsonify({"message": "User blocked."})


@api_bp.route("/admin/users/<int:user_id>/unblock", methods=["POST"])
@admin_required
def admin_unblock(user_id: int):
    user = _get_user_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    return jsonify({"message": "User unblocked."})


@api_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def admin_delete(user_id: int):
    user = _get_user_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"error": "You cannot delete your own account."}), 400
    if user.is_admin and User.query.filter_by(role=UserRole.ADMIN).count() <= 1:
        return jsonify({"error": "The last administrator cannot be removed."}), 400
    image_service.delete_user_images(user)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"deleted": True})
