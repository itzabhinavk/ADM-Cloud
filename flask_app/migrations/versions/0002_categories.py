"""Add user-owned image categories."""

import sqlalchemy as sa
from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.add_column("images", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_images_category_id", "images", "categories", ["category_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_images_category_id", "images", ["category_id"])


def downgrade():
    op.drop_index("ix_images_category_id", table_name="images")
    op.drop_constraint("fk_images_category_id", "images", type_="foreignkey")
    op.drop_column("images", "category_id")
    op.drop_index("ix_categories_user_id", table_name="categories")
    op.drop_table("categories")
