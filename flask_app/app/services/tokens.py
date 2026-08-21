"""Secure, hashed, expiring email tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import EmailToken, TokenPurpose


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_token(user, purpose: str = TokenPurpose.EMAIL_VERIFICATION) -> str:
    """Invalidate previous tokens of the same purpose and return a new raw token."""
    EmailToken.query.filter_by(user_id=user.id, purpose=purpose, used_at=None).delete()
    raw = secrets.token_urlsafe(32)
    max_age = int(current_app.config.get("VERIFICATION_TOKEN_MAX_AGE", 86400))
    token = EmailToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=max_age),
    )
    db.session.add(token)
    db.session.commit()
    return raw


def consume_token(raw_token: str, purpose: str = TokenPurpose.EMAIL_VERIFICATION):
    """Return the owning user if the token is valid, else None. Single use."""
    if not raw_token:
        return None
    token = EmailToken.query.filter_by(
        token_hash=hash_token(raw_token), purpose=purpose
    ).first()
    if token is None or not token.is_usable:
        return None
    token.used_at = datetime.now(timezone.utc)
    db.session.add(token)
    return token.user
