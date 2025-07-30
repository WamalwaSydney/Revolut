"""Add language support

Revision ID: 37bb9bdf567b
Revises: ca1ce1712045
Create Date: 2025-07-30 10:35:06.323706

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '37bb9bdf567b'
down_revision = 'ca1ce1712045'
branch_labels = None
depends_on = None


def upgrade():
    """Database migration for language support"""
    from alembic import op
    import sqlalchemy as sa

    # Add language column to users table
    op.add_column('user', sa.Column('language', sa.String(2), default='en'))

    # Add indices for better performance
    op.create_index('idx_user_language', 'user', ['language'])
    op.create_index('idx_feedback_language', 'user_feedback', ['language'])

    # Update existing records to have default language
    op.execute("UPDATE \"user\" SET language = 'en' WHERE language IS NULL")
    op.execute("UPDATE user_feedback SET language = 'en' WHERE language IS NULL")

    # ### end Alembic commands ###
