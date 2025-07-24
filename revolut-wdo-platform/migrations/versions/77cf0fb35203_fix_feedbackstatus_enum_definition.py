"""Fix feedbackstatus ENUM definition

Revision ID: 77cf0fb35203
Revises:
Create Date: 2025-07-23 22:43:27.813230

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77cf0fb35203'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Enum('pending', 'reviewed', 'in_progress', 'resolved', 'rejected', name='feedbackstatus'), nullable=True))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=256),
               nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=256),
               nullable=True)

    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_column('status')
