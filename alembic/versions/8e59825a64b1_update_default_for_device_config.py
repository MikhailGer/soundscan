"""update default for device_config

Revision ID: 8e59825a64b1
Revises: cd55e84eb28c
Create Date: 2024-11-24 19:43:55.076947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e59825a64b1'
down_revision: Union[str, None] = 'cd55e84eb28c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:  # ... (previous alter_column statements)
    # Update existing NULL values to the default values
    op.execute("""        UPDATE soundscan.device_config
        SET searching_time = 10000 WHERE searching_time IS NULL;    """)
    op.execute("""        UPDATE soundscan.device_config
        SET circle_in_steps = 14400 WHERE circle_in_steps IS NULL;    """)
    op.execute("""        UPDATE soundscan.device_config
        SET recording_time = 3000 WHERE recording_time IS NULL;    """)
    op.execute("""        UPDATE soundscan.device_config
        SET force_to_find = 50 WHERE force_to_find IS NULL;    """)


def downgrade() -> None:
    pass
