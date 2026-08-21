"""Authenticated dashboard pages."""

from flask import Blueprint, render_template, request
from flask_login import current_user
from sqlalchemy import func

from ..extensions import db
from ..models import Category, Image
from ..utils.decorators import verified_required

dashboard_bp = Blueprint("dashboard", __name__)

PER_PAGE = 24


@dashboard_bp.route("/dashboard")
@verified_required
def index():
    query = current_user.images.order_by(Image.uploaded_at.desc())
    search = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id", type=int)
    if search:
        query = query.filter(Image.original_filename.ilike(f"%{search[:100]}%"))
    if category_id:
        query = query.filter(Image.category_id == category_id)

    page = max(1, request.args.get("page", 1, type=int))
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    totals = db.session.query(
        func.count(Image.id), func.coalesce(func.sum(Image.file_size), 0)
    ).filter(Image.user_id == current_user.id).one()

    return render_template(
        "dashboard/index.html",
        images=pagination.items,
        pagination=pagination,
        search=search,
        total_images=totals[0],
        total_bytes=totals[1],
        categories=current_user.categories.order_by(Category.name).all(),
        selected_category_id=category_id,
    )
