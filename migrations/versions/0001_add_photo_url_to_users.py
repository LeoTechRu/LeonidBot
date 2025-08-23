"""Add photo_url to users

Revision ID: 0001_add_photo_url_to_users
Revises: 
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_add_photo_url_to_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("photo_url", sa.String(length=255)))


def downgrade() -> None:
    op.drop_column("users", "photo_url")

