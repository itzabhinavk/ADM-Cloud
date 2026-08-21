"""Admin area. Every route is gated by @admin_required on the server."""

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from ..extensions import db
from ..forms import EmptyForm
from ..models import Image, User, UserRole
from ..services import image_service
from ..utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__)

PER_PAGE = 25


def _admin_count() -> int:
    return User.query.filter_by(role=UserRole.ADMIN, is_blocked=False).count()


def _get_user_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        abort(404, description="User not found.")
    return user


@admin_bp.route("/")
@admin_required
def index():
    total_users = User.query.count()
    verified_users = User.query.filter_by(email_verified=True).count()
    blocked_users = User.query.filter_by(is_blocked=True).count()
    total_images, total_bytes = db.session.query(
        func.count(Image.id), func.coalesce(func.sum(Image.file_size), 0)
    ).one()
    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()
    recent_images = Image.query.order_by(Image.uploaded_at.desc()).limit(8).all()

    return render_template(
        "admin/index.html",
        total_users=total_users,
        verified_users=verified_users,
        blocked_users=blocked_users,
        total_images=total_images,
        total_bytes=total_bytes,
        recent_users=recent_users,
        recent_images=recent_images,
    )


@admin_bp.route("/users")
@admin_required
def users():
    page = max(1, request.args.get("page", 1, type=int))
    search = (request.args.get("q") or "").strip()
    query = User.query
    if search:
        query = query.filter(User.email.ilike(f"%{search[:100]}%"))
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    counts = dict(
        db.session.query(Image.user_id, func.count(Image.id)).group_by(Image.user_id).all()
    )
    return render_template(
        "admin/users.html",
        users=pagination.items,
        pagination=pagination,
        search=search,
        counts=counts,
        form=EmptyForm(),
    )


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = _get_user_or_404(user_id)
    images = user.images.order_by(Image.uploaded_at.desc()).limit(24).all()
    total_bytes = (
        db.session.query(func.coalesce(func.sum(Image.file_size), 0))
        .filter(Image.user_id == user.id)
        .scalar()
    )
    return render_template(
        "admin/user_detail.html",
        user=user,
        images=images,
        total_bytes=total_bytes,
        form=EmptyForm(),
    )


def _respond(message: str, category: str = "success", status: int = 200):
    if request.path.startswith("/api/"):
        return jsonify({"message": message}), status
    flash(message, category)
    return redirect(request.referrer or url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/block", methods=["POST"])
@admin_required
def block_user(user_id: int):
    user = _get_user_or_404(user_id)
    if user.id == current_user.id:
        return _respond("You cannot block your own account.", "error", 400)
    if user.is_admin and _admin_count() <= 1:
        return _respond("At least one active administrator must remain.", "error", 400)
    user.is_blocked = True
    db.session.commit()
    return _respond("User blocked.")


@admin_bp.route("/users/<int:user_id>/unblock", methods=["POST"])
@admin_required
def unblock_user(user_id: int):
    user = _get_user_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    return _respond("User unblocked.")


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    user = _get_user_or_404(user_id)
    if user.id == current_user.id:
        return _respond("You cannot delete your own account.", "error", 400)
    if user.is_admin and User.query.filter_by(role=UserRole.ADMIN).count() <= 1:
        return _respond("The last administrator cannot be removed.", "error", 400)

    image_service.delete_user_images(user)
    db.session.delete(user)
    db.session.commit()
    if request.path.startswith("/api/"):
        return jsonify({"deleted": True}), 200
    flash("User and all of their images were removed.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/images")
@admin_required
def images():
    page = max(1, request.args.get("page", 1, type=int))
    pagination = Image.query.order_by(Image.uploaded_at.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    return render_template(
        "admin/images.html", images=pagination.items, pagination=pagination
    )
