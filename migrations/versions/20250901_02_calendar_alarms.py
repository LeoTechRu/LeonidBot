"""create calendar_alarms table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250901_02'
down_revision = '20250901_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'calendar_alarms',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.Integer, sa.ForeignKey('calendar_events.id'), nullable=False),
        sa.Column('owner_id', sa.BigInteger, sa.ForeignKey('users_tg.telegram_id'), nullable=False),
        sa.Column('notify_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('calendar_alarms')
