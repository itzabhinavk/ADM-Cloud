"""Upload validation: extension + sniffed content + real decode."""

import io
import os
import secrets

from flask import current_app
from werkzeug.utils import secure_filename

EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


class ValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _extension(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower().lstrip(".")


def validate_upload(file_storage) -> dict:
    """Return validated metadata or raise ValidationError. Never trusts the client."""
    if file_storage is None or not (file_storage.filename or "").strip():
        raise ValidationError("No file was provided.")

    original_filename = secure_filename(file_storage.filename)[:255] or "upload"
    ext = _extension(original_filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("That file type is not supported.")

    data = file_storage.read()
    file_storage.seek(0)
    size = len(data)
    if size == 0:
        raise ValidationError("The uploaded file is empty.")

    max_size = int(current_app.config["UPLOAD_MAX_SIZE"])
    if size > max_size:
        raise ValidationError("That file is larger than the allowed limit.", 413)

    try:
        from PIL import Image as PILImage

        with PILImage.open(io.BytesIO(data)) as probe:
            probe.verify()
        with PILImage.open(io.BytesIO(data)) as probe:
            pil_format = (probe.format or "").upper()
            width, height = probe.size
    except ValidationError:
        raise
    except Exception:  # noqa: BLE001
        raise ValidationError("That file could not be read as an image.")

    detected_mime = PIL_FORMAT_TO_MIME.get(pil_format)
    if not detected_mime:
        raise ValidationError("That image format is not supported.")

    allowed = current_app.config["ALLOWED_IMAGE_TYPES"]
    if detected_mime not in allowed:
        raise ValidationError("That image format is not supported.")

    canonical_ext = EXTENSION_BY_MIME[detected_mime]
    stored_name = f"{secrets.token_hex(16)}.{canonical_ext}"

    return {
        "data": data,
        "original_filename": original_filename,
        "filename": stored_name,
        "mime_type": detected_mime,
        "file_size": size,
        "width": width,
        "height": height,
    }
