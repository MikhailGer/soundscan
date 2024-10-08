"""Update default values for DeviceConfig

Revision ID: abeeab6f9ebc
Revises: 7951af881f3c
Create Date: 2024-10-07 22:09:44.190760

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8d9f274a704f'
down_revision: Union[str, None] = '7951af881f3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.alter_column('device_config', 'base_motor_speed',
                    existing_type=sa.Float(),
                    server_default=sa.text("800"),schema='soundscan')
    op.alter_column('device_config', 'base_motor_accel',
                    existing_type=sa.Float(),
                    server_default=sa.text("1600"),schema='soundscan')
    op.alter_column('device_config', 'base_motor_MaxSpeed',
                    existing_type=sa.Float(),
                    server_default=sa.text("8000"),schema='soundscan')
    op.alter_column('device_config', 'head_motor_speed',
                    existing_type=sa.Float(),
                    server_default=sa.text("800"),schema='soundscan')
    op.alter_column('device_config', 'head_motor_accel',
                    existing_type=sa.Float(),
                    server_default=sa.text("1600"),schema='soundscan')
    op.alter_column('device_config', 'head_motor_MaxSpeed',
                    existing_type=sa.Float(),
                    server_default=sa.text("8000"),schema='soundscan')
    op.alter_column('device_config', 'head_motor_returning_speed',
                    existing_type=sa.Float(),
                    server_default=sa.text("2000"),schema='soundscan')
    op.alter_column('device_config', 'head_motor_returning_accel',
                    existing_type=sa.Float(),
                    server_default=sa.text("3200"),schema='soundscan')


def downgrade() -> None:
    op.alter_column('device_config', 'base_motor_speed',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'base_motor_accel',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'base_motor_MaxSpeed',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'head_motor_speed',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'head_motor_accel',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'head_motor_MaxSpeed',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения
    op.alter_column('device_config', 'head_motor_returning_speed',
                    existing_type=sa.Float(),
                    server_default=None, schema='soundscan')  # Замените None на предыдущие значения