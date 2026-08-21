"""Server-side authorization helpers. UI never decides access."""

from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    return request.accept_mimetypes.best == "application/json"


def _deny(status: int, message: str):
    if _wants_json():
        abort(status, description=message)
    if status == 401:
        flash(message, "info")
        return redirect(url_for("auth.login", next=request.full_path))
    abort(status, description=message)


def login_required_api(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _deny(401, "Authentication required.")
        if current_user.is_blocked:
            return _deny(403, "This account has been suspended.")
        return view(*args, **kwargs)

    return wrapper


def verified_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _deny(401, "Authentication required.")
        if current_user.is_blocked:
            return _deny(403, "This account has been suspended.")
        if not current_user.email_verified:
            if _wants_json():
                return _deny(403, "Please verify your email address first.")
            flash("Please verify your email address to continue.", "warning")
            return redirect(url_for("auth.verify_notice"))
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _deny(401, "Authentication required.")
        if current_user.is_blocked or not current_user.is_admin:
            return _deny(403, "You do not have access to this area.")
        return view(*args, **kwargs)

    return wrapper
