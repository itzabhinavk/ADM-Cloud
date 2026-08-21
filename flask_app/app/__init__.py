"""Application factory."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from .config import get_config
from .extensions import csrf, db, limiter, login_manager, migrate, oauth
from .utils.formatting import human_datetime, human_filesize
from .utils.security_headers import apply_security_headers

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env", override=False)

ERROR_TITLES = {
    400: "Bad request",
    401: "Sign in required",
    403: "Access denied",
    404: "Page not found",
    413: "File too large",
    429: "Too many requests",
    500: "Something went wrong",
}


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)
    _register_oauth(app)

    from . import models  # noqa: F401  (register mappers)
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id)) if user_id else None

    _register_blueprints(app)
    _register_errors(app)
    _register_context(app)
    _register_cli(app)

    app.after_request(apply_security_headers)
    app.jinja_env.filters["filesize"] = human_filesize
    app.jinja_env.filters["datetime"] = human_datetime

    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    return app


def _register_blueprints(app: Flask) -> None:
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.images import images_bp
    from .routes.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(images_bp, url_prefix="/api/images")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # CSRF stays enabled for every blueprint; browser JSON calls send the
    # token in the X-CSRFToken header (see static/js/app.js).


def _register_oauth(app: Flask) -> None:
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    if app.config.get("GITHUB_CLIENT_ID") and app.config.get("GITHUB_CLIENT_SECRET"):
        oauth.register(
            name="github",
            client_id=app.config["GITHUB_CLIENT_ID"],
            client_secret=app.config["GITHUB_CLIENT_SECRET"],
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "read:user user:email"},
        )


def _wants_json() -> bool:
    return request.path.startswith("/api/") or (
        request.accept_mimetypes.best == "application/json"
    )


def _register_errors(app: Flask) -> None:
    def handler(status: int):
        def _handle(error):
            description = getattr(error, "description", None)
            message = description if isinstance(description, str) else ERROR_TITLES[status]
            if status == 500:
                app.logger.exception("Unhandled error on %s", request.path)
                message = "An unexpected error occurred."
            if _wants_json():
                return jsonify({"error": message, "status": status}), status
            return (
                render_template(
                    "errors/error.html",
                    status=status,
                    title=ERROR_TITLES[status],
                    message=message,
                ),
                status,
            )

        return _handle

    for code in ERROR_TITLES:
        app.register_error_handler(code, handler(code))

    from .services.image_validation import ValidationError
    from .services.storage_service import StorageError

    @app.errorhandler(ValidationError)
    def _validation(error):  # pragma: no cover - exercised via routes
        if _wants_json():
            return jsonify({"error": error.message}), error.status_code
        return handler(error.status_code)(error)

    @app.errorhandler(StorageError)
    def _storage(error):  # pragma: no cover - exercised via routes
        app.logger.error("Storage error: %s", error)
        if _wants_json():
            return jsonify({"error": str(error)}), 502
        return handler(500)(error)


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_branding():
        cfg = app.config
        return {
            "branding": {
                "name": cfg["APP_NAME"],
                "logo_url": cfg["APP_LOGO_URL"],
                "favicon_url": cfg["APP_FAVICON_URL"],
                "primary": cfg["APP_PRIMARY_COLOR"],
                "secondary": cfg["APP_SECONDARY_COLOR"],
                "support_email": cfg["SUPPORT_EMAIL"],
                "base_url": cfg["APP_BASE_URL"],
            },
            "max_upload_size": cfg["UPLOAD_MAX_SIZE"],
        }


def _register_cli(app: Flask) -> None:
    from .cli import register_cli

    register_cli(app)


__all__ = ["create_app", "db"]
