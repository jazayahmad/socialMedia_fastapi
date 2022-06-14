"""add users table

Revision ID: 02851035bf8b
Revises: b87239aaf195
Create Date: 2022-06-14 18:33:56.814671

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02851035bf8b'
down_revision = 'b87239aaf195'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('email', sa.String(), nullable=False),
                    sa.Column('password', sa.String(), nullable=False),
                    sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('email')
                    )
    pass


def downgrade():
    op.drop_table('users')
    pass
