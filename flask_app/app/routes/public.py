"""Landing page and the public image delivery route."""

import urllib.error
import urllib.request

from flask import Blueprint, Response, abort, current_app, jsonify, render_template

from ..models import Image

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")


@public_bp.route("/manifest.webmanifest")
def manifest():
    """Installable web-app manifest, driven entirely by branding env vars."""
    cfg = current_app.config
    icons = []
    if cfg.get("APP_LOGO_URL"):
        icons.append(
            {"src": cfg["APP_LOGO_URL"], "sizes": "512x512", "type": "image/png"}
        )
    response = jsonify(
        {
            "name": cfg["APP_NAME"],
            "short_name": cfg["APP_NAME"],
            "description": "Private image hosting with permanent links.",
            "start_url": "/dashboard",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#f6f7fb",
            "theme_color": cfg["APP_PRIMARY_COLOR"],
            "icons": icons,
        }
    )
    response.headers["Content-Type"] = "application/manifest+json"
    return response



@public_bp.route("/i/<slug>")
def serve_image(slug: str):
    """Branded, login-free public URL. 404 once the image is deleted."""
    if not slug or len(slug) > 32 or not slug.isalnum():
        abort(404)
    image = Image.query.filter_by(public_slug=slug).first()
    if image is None:
        abort(404)
    try:
        with urllib.request.urlopen(image.secure_url or image.storage_url, timeout=20) as upstream:
            payload = upstream.read()
            content_type = upstream.headers.get_content_type() or image.mime_type
    except (urllib.error.URLError, TimeoutError, OSError):
        abort(404)
    response = Response(payload, content_type=content_type)
    response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@public_bp.route("/healthz")
def healthz():
    return {"status": "ok"}
