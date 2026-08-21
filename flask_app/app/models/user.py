from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole:
    USER = "user"
    ADMIN = "admin"
    ALL = (USER, ADMIN)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER, index=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)
    github_id = db.Column(db.String(255), unique=True, nullable=True, index=True)

    images = db.relationship(
        "Image", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    tokens = db.relationship(
        "EmailToken", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    categories = db.relationship(
        "Category", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        db.CheckConstraint("role in ('user','admin')", name="ck_users_role"),
    )

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def normalize_email(email: str) -> str:
        return (email or "").strip().lower()

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password or "")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_active(self) -> bool:  # consulted by Flask-Login
        return not self.is_blocked

    def to_dict(self, include_admin_fields: bool = False) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_admin_fields:
            data.update(
                {
                    "role": self.role,
                    "is_blocked": self.is_blocked,
                    "last_login_at": self.last_login_at.isoformat()
                    if self.last_login_at
                    else None,
                }
            )
        return data

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.id}>"
