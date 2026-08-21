"""Add Google and GitHub identity fields."""

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("github_id", sa.String(length=255), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)


def downgrade():
    op.drop_index("ix_users_github_id", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "github_id")
    op.drop_column("users", "google_sub")