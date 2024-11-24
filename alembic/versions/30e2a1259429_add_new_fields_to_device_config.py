"""Add new fields to device_config

Revision ID: 30e2a1259429
Revises: 7ae1b424ca60
Create Date: 2024-11-24 18:52:20.357933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pydantic.v1.schema import schema

# revision identifiers, used by Alembic.
revision: str = '30e2a1259429'
down_revision: Union[str, None] = '7ae1b424ca60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('device_config',
                  sa.Column('searching_time', sa.Integer, nullable= True),
                  schema = 'soundscan'
                  )
    op.add_column('device_config',
                  sa.Column('circle_in_steps', sa.Integer, nullable=True),
                  schema='soundscan'
                  )
    op.add_column('device_config',
                  sa.Column('recording_time', sa.Integer, nullable=True),
                  schema='soundscan'
                  )
    op.add_column('device_config',
                  sa.Column('force_to_find', sa.Integer, nullable=True),
                  schema='soundscan'
                  )

def downgrade() -> None:
    op.drop_column('device_config','searching_time',schema='soundscan')
    op.drop_column('device_config','circle_in_steps',schema='soundscan')
    op.drop_column('device_config', 'recording_time',schema='soundscan')
    op.drop_column('device_config','force_to_find',chema='soundscan')