from datetime import datetime, timezone

from ..extensions import db
from .user import utcnow


class TokenPurpose:
    EMAIL_VERIFICATION = "email_verification"
    ALL = (EMAIL_VERIFICATION,)


class EmailToken(db.Model):
    """Only the SHA-256 hash of the token is persisted."""

    __tablename__ = "email_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    purpose = db.Column(
        db.String(50), nullable=False, default=TokenPurpose.EMAIL_VERIFICATION
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="tokens")

    @property
    def is_expired(self) -> bool:
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expires

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired
