"""Update default values in DiskType

Revision ID: cf4d9cd2e3ad
Revises: 831038e36e23
Create Date: 2024-09-26 18:58:32.369410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf4d9cd2e3ad'
down_revision: Union[str, None] = '831038e36e23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменение значений по умолчанию для колонки blade_force и остальных полей
    op.alter_column('disk_type', 'blade_force', schema='soundscan', server_default='0')
    op.alter_column('disk_type', 'diameter', schema='soundscan', server_default='0')
    op.alter_column('disk_type', 'blade_distance', schema='soundscan', server_default='0')
    op.alter_column('disk_type', 'name', schema='soundscan', server_default="New disk type")
    op.alter_column('disk_type', 'created_at', schema='soundscan', server_default=sa.text('now()'))


def downgrade() -> None:
    # Откат изменений значений по умолчанию
    op.alter_column('disk_type', 'blade_force', schema='soundscan', server_default=None)
    op.alter_column('disk_type', 'diameter', schema='soundscan', server_default=None)
    op.alter_column('disk_type', 'blade_distance', schema='soundscan', server_default=None)
    op.alter_column('disk_type', 'name', schema='soundscan', server_default=None)
    op.alter_column('disk_type', 'created_at', schema='soundscan', server_default=None)

