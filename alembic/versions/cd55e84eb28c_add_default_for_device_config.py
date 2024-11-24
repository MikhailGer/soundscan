"""Add default for device_config

Revision ID: cd55e84eb28c
Revises: 30e2a1259429
Create Date: 2024-11-24 19:40:05.902084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd55e84eb28c'
down_revision: Union[str, None] = '30e2a1259429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('device_config', 'searching_time',
                    existing_type=sa.Integer(),
                    server_default=sa.text('10000'),
                    schema='soundscan')
    op.alter_column('device_config', 'circle_in_steps',
                    existing_type=sa.Integer(),
                    server_default=sa.text('14400'),
                    schema='soundscan')
    op.alter_column('device_config', 'recording_time',
                    existing_type=sa.Integer(),
                    server_default=sa.text('3000'),
                    schema='soundscan')
    op.alter_column('device_config', 'force_to_find',
                    existing_type=sa.Integer(),
                    server_default=sa.text('50'),
                    schema='soundscan')


def downgrade() -> None:
    pass
