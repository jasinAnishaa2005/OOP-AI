"""add exam idempotency key

Revision ID: 5b1e0c7d2a91
Revises: 47ad6377bf43
Create Date: 2026-11-23 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5b1e0c7d2a91'
down_revision: Union[str, None] = '47ad6377bf43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('exams') as batch_op:
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=100), nullable=True))
        batch_op.create_unique_constraint('uq_exams_user_idempotency_key', ['user_id', 'idempotency_key'])


def downgrade() -> None:
    with op.batch_alter_table('exams') as batch_op:
        batch_op.drop_constraint('uq_exams_user_idempotency_key', type_='unique')
        batch_op.drop_column('idempotency_key')
