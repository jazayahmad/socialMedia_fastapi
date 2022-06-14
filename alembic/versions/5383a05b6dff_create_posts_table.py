"""Create Posts Table

Revision ID: 5383a05b6dff
Revises: 
Create Date: 2022-06-13 20:55:05.809339

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5383a05b6dff'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('posts', sa.Column('id', sa.Integer(), nullable = False, primary_key = True),
                    sa.Column('title', sa.String(), nullable = False))
    pass


def downgrade():
    op.drop_table("posts")
    pass
