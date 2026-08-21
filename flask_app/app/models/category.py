from ..extensions import db
from .user import utcnow


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="categories")
    images = db.relationship("Image", back_populates="category")

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    )
