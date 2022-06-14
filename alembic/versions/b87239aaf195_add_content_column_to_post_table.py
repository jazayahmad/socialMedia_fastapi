"""add content column to post table

Revision ID: b87239aaf195
Revises: 5383a05b6dff
Create Date: 2022-06-14 18:18:35.611365

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b87239aaf195'
down_revision = '5383a05b6dff'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts",sa.Column('content', sa.String(), nullable=False))
    pass


def downgrade():
    op.drop_column("posts","content")
    pass
