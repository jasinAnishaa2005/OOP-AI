"""durable generation recovery, usage outcomes and shared rate limits

Revision ID: 8e2f4a6b9c13
Revises: 5b1e0c7d2a91
Create Date: 2026-11-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8e2f4a6b9c13'
down_revision: Union[str, None] = '5b1e0c7d2a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('rate_limit_buckets',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('window_start', sa.BigInteger(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('key', 'window_start')
    )
    op.create_index(op.f('ix_rate_limit_buckets_expires_at'), 'rate_limit_buckets', ['expires_at'], unique=False)
    with op.batch_alter_table('exams') as batch_op:
        batch_op.add_column(sa.Column('generation_runs', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('idempotency_hash', sa.String(length=64), nullable=True))
    with op.batch_alter_table('exam_generation_requests') as batch_op:
        batch_op.add_column(sa.Column('outcome', sa.String(length=20), server_default='pending', nullable=False))
        batch_op.create_index(batch_op.f('ix_exam_generation_requests_exam_id'), ['exam_id'], unique=False)
    # Existing usage: ready exams succeeded, failed exams no longer count toward the daily limit.
    op.execute(
        "UPDATE exam_generation_requests SET outcome = 'succeeded' "
        "WHERE exam_id IN (SELECT id FROM exams WHERE status = 'ready')"
    )
    op.execute(
        "UPDATE exam_generation_requests SET outcome = 'failed' "
        "WHERE exam_id IN (SELECT id FROM exams WHERE status = 'failed')"
    )


def downgrade() -> None:
    with op.batch_alter_table('exam_generation_requests') as batch_op:
        batch_op.drop_index(batch_op.f('ix_exam_generation_requests_exam_id'))
        batch_op.drop_column('outcome')
    with op.batch_alter_table('exams') as batch_op:
        batch_op.drop_column('idempotency_hash')
        batch_op.drop_column('generation_runs')
    op.drop_index(op.f('ix_rate_limit_buckets_expires_at'), table_name='rate_limit_buckets')
    op.drop_table('rate_limit_buckets')
