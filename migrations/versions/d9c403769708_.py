"""empty message

Revision ID: d9c403769708
Revises: 
Create Date: 2018-12-31 06:10:15.825115

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9c403769708'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rma', sa.Column('serialnumber', sa.String(length=25), nullable=False))
    op.create_unique_constraint(None, 'rma', ['serialnumber'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'rma', type_='unique')
    op.drop_column('rma', 'serialnumber')
    # ### end Alembic commands ###