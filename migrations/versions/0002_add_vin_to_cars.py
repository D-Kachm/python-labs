"""add vin column with unique constraint to cars table

Revision ID: 0002_add_vin_to_cars
Revises: 0001_initial_tables
Create Date: 2026-10-24 14:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_add_vin_to_cars'
down_revision: Union[str, Sequence[str], None] = '0001_initial_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('cars', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vin', sa.String(length=17), nullable=True))
        batch_op.create_unique_constraint('uq_cars_vin', ['vin'])

def downgrade() -> None:
    with op.batch_alter_table('cars', schema=None) as batch_op:
        batch_op.drop_constraint('uq_cars_vin', type_='unique')
        batch_op.drop_column('vin')
