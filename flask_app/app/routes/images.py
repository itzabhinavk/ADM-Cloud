"""JSON image endpoints. Ownership is enforced server-side on every call."""

from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import func

from ..extensions import limiter
from ..models import Category, Image
from ..extensions import db
from ..services import image_service
from ..services.image_validation import ValidationError
from ..services.storage_service import StorageError
from ..utils.decorators import verified_required

images_bp = Blueprint("images", __name__)


def _owned_image_or_abort(slug: str) -> Image:
    image = Image.query.filter_by(public_slug=slug).first()
    if image is None:
        abort(404, description="Image not found.")
    if image.user_id != current_user.id and not current_user.is_admin:
        # Ownership failure is a 403, never a silent success.
        abort(403, description="You do not have access to this image.")
    return image


@images_bp.route("/stats", methods=["GET"])
@verified_required
def stats():
    count, total_bytes = db.session.query(
        func.count(Image.id), func.coalesce(func.sum(Image.file_size), 0)
    ).filter(Image.user_id == current_user.id).one()
    return jsonify({"count": count, "total_bytes": int(total_bytes or 0)})


@images_bp.route("", methods=["GET"])
@images_bp.route("/", methods=["GET"])
@verified_required
def list_images():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 24, type=int)))
    pagination = (
        current_user.images.order_by(Image.uploaded_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify(
        {
            "images": [image.to_dict() for image in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@images_bp.route("/categories", methods=["GET", "POST"])
@verified_required
def categories():
    if request.method == "GET":
        items = current_user.categories.order_by(Category.name).all()
        return jsonify({"categories": [{"id": item.id, "name": item.name} for item in items]})

    payload = request.get_json(silent=True) or {}
    name = " ".join(str(payload.get("name", "")).split())
    if not name or len(name) > 100:
        return jsonify({"error": "Category name must be between 1 and 100 characters."}), 400
    category = Category(user_id=current_user.id, name=name)
    db.session.add(category)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "That category already exists."}), 409
    return jsonify({"category": {"id": category.id, "name": category.name}}), 201


@images_bp.route("/upload", methods=["POST"])
@verified_required
@limiter.limit(lambda: current_app.config.get("RATELIMIT_UPLOAD", "60 per hour"))
def upload():
    file_storage = request.files.get("file") or request.files.get("image")
    category_id = request.form.get("category_id", type=int)
    category = None
    if category_id:
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if category is None:
            return jsonify({"error": "Invalid category selected."}), 400
    try:
        image = image_service.create_image(current_user, file_storage, category=category)
    except ValidationError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except StorageError as exc:
        current_app.logger.error("Upload failed: %s", exc)
        return jsonify({"error": str(exc)}), 502
    return jsonify({"image": image.to_dict()}), 201


@images_bp.route("/<slug>", methods=["DELETE"])
@verified_required
def delete(slug: str):
    image = _owned_image_or_abort(slug)
    image_service.delete_image(image)
    return jsonify({"deleted": True, "slug": slug})


@images_bp.route("/<slug>", methods=["GET"])
@verified_required
def detail(slug: str):
    image = _owned_image_or_abort(slug)
    return jsonify({"image": image.to_dict()})
