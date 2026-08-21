"""Image storage/CDN backend.

Cloudinary is an implementation detail of this module only. The rest of the
application talks to the generic helpers below, so the provider can be swapped
without touching routes, models or templates.
"""

import io
import os

from flask import current_app


class StorageError(Exception):
    pass


def _client():
    import cloudinary

    cfg = current_app.config
    if not (
        cfg.get("CLOUDINARY_CLOUD_NAME")
        and cfg.get("CLOUDINARY_API_KEY")
        and cfg.get("CLOUDINARY_API_SECRET")
    ):
        raise StorageError("Image storage is not configured.")
    cloudinary.config(
        cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
        api_key=cfg["CLOUDINARY_API_KEY"],
        api_secret=cfg["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    return cloudinary


def upload_image(data: bytes, filename: str) -> dict:
    """Upload bytes and return normalised metadata."""
    _client()
    import cloudinary.uploader

    folder = current_app.config.get("CLOUDINARY_UPLOAD_FOLDER") or None
    public_id = os.path.splitext(filename)[0]
    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(data),
            folder=folder,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            unique_filename=False,
            use_filename=False,
            invalidate=True,
        )
    except StorageError:
        raise
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error("Storage upload failed: %s", type(exc).__name__)
        raise StorageError("The image could not be stored. Please try again.") from exc

    secure_url = result.get("secure_url") or result.get("url")
    if not result.get("public_id") or not secure_url:
        raise StorageError("The storage backend returned an unexpected response.")

    return {
        "public_id": result["public_id"],
        "url": result.get("url") or secure_url,
        "secure_url": secure_url,
        "width": result.get("width"),
        "height": result.get("height"),
        "bytes": result.get("bytes"),
    }


def delete_image(public_id: str) -> bool:
    """Best-effort removal of a stored asset."""
    if not public_id:
        return False
    try:
        _client()
        import cloudinary.uploader

        result = cloudinary.uploader.destroy(public_id, invalidate=True)
        return result.get("result") in {"ok", "not found"}
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(
            "Storage delete failed for asset: %s", type(exc).__name__
        )
        return False
