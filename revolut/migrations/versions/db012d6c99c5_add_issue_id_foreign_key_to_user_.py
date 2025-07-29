"""Add issue_id foreign key to user_feedback

Revision ID: db012d6c99c5
Revises: 4a11d35e1db7
Create Date: 2025-07-29 10:33:59.859582
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'db012d6c99c5'
down_revision = '4a11d35e1db7'
branch_labels = None
depends_on = None


def upgrade():
    # Alter issue table
    with op.batch_alter_table('issue', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('contact', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('title',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=200),
               existing_nullable=False)
        batch_op.alter_column('description',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('location',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)

    # Update user table - truncate password_hash if too long
    op.execute("""
        UPDATE "user"
        SET password_hash = LEFT(password_hash, 128)
        WHERE LENGTH(password_hash) > 128
    """)

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
            existing_type=sa.VARCHAR(length=255),
            type_=sa.String(length=128),
            existing_nullable=True)

    # Alter user_feedback table
    with op.batch_alter_table('user_feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('issue_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('contact', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=20), nullable=True))
        # Recreate the user_id foreign key constraint
        batch_op.drop_constraint('user_feedback_user_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key('user_feedback_user_id_fkey', 'user', ['user_id'], ['id'])
        # Add foreign key constraint for issue_id
        batch_op.create_foreign_key('user_feedback_issue_id_fkey', 'issue', ['issue_id'], ['id'])
        # Drop columns that are no longer needed
        batch_op.drop_column('audio_url')
        batch_op.drop_column('tags')
        batch_op.drop_column('is_processed')


def downgrade():
    # Reverse changes in user_feedback
    with op.batch_alter_table('user_feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_processed', sa.BOOLEAN(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('audio_url', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
        # Drop foreign key constraints
        batch_op.drop_constraint('user_feedback_issue_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('user_feedback_user_id_fkey', type_='foreignkey')
        # Recreate original user_id foreign key
        batch_op.create_foreign_key('user_feedback_user_id_fkey', 'user', ['user_id'], ['id'])
        # Drop new columns
        batch_op.drop_column('source')
        batch_op.drop_column('contact')
        batch_op.drop_column('issue_id')

    # Reverse changes in user
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.String(length=128),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)

    # Reverse changes in issue
    with op.batch_alter_table('issue', schema=None) as batch_op:
        batch_op.alter_column('location',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.alter_column('description',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('title',
               existing_type=sa.String(length=200),
               type_=sa.VARCHAR(length=100),
               existing_nullable=False)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('contact')
        batch_op.drop_column('priority')