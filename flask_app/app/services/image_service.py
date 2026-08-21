"""Image lifecycle: validate -> store -> persist, with rollback on failure."""

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Image
from ..models.image import generate_slug
from . import storage_service
from .image_validation import ValidationError, validate_upload


def _unique_slug() -> str:
    for _ in range(10):
        slug = generate_slug()
        if not Image.query.filter_by(public_slug=slug).first():
            return slug
    raise ValidationError("Could not allocate an image identifier.", 500)


def create_image(user, file_storage, category=None) -> Image:
    meta = validate_upload(file_storage)

    stored = storage_service.upload_image(meta["data"], meta["filename"])

    image = Image(
        public_slug=_unique_slug(),
        user_id=user.id,
        category_id=category.id if category else None,
        filename=meta["filename"],
        original_filename=meta["original_filename"],
        storage_public_id=stored["public_id"],
        storage_url=stored["url"],
        secure_url=stored["secure_url"],
        file_size=stored.get("bytes") or meta["file_size"],
        mime_type=meta["mime_type"],
        width=stored.get("width") or meta["width"],
        height=stored.get("height") or meta["height"],
    )
    try:
        db.session.add(image)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        # Do not leave an orphaned asset behind.
        storage_service.delete_image(stored["public_id"])
        current_app.logger.error("Image persistence failed: %s", type(exc).__name__)
        raise storage_service.StorageError("The upload could not be saved.") from exc
    return image


def delete_image(image: Image) -> None:
    """Remove the stored asset first, then the row."""
    storage_service.delete_image(image.storage_public_id)
    db.session.delete(image)
    db.session.commit()


def delete_user_images(user) -> int:
    images = list(user.images)
    for image in images:
        storage_service.delete_image(image.storage_public_id)
        db.session.delete(image)
    db.session.commit()
    return len(images)
