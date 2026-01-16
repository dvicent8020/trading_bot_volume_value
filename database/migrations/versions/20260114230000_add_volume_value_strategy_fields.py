"""add_volume_value_strategy_fields

Revision ID: 20260114230000
Revises: 20260114224810
Create Date: 2026-01-14 23:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260114230000'
down_revision: Union[str, Sequence[str], None] = '20260114224810'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar campos de Volume Value Strategy a strategy_configs
    op.add_column('strategy_configs', sa.Column('vwap_period_days', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('volume_profile_period', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('value_area_percent', sa.Float(), nullable=True))
    op.add_column('strategy_configs', sa.Column('delta_lookback_vv', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('volatility_threshold', sa.Float(), nullable=True))
    op.add_column('strategy_configs', sa.Column('min_volume_period', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('lvn_lookback', sa.Integer(), nullable=True))
    
    # Agregar campos a signals para VolumeValueStrategy
    op.add_column('signals', sa.Column('vwap_value', sa.Float(), nullable=True))
    op.add_column('signals', sa.Column('vpoc_level', sa.Float(), nullable=True))
    op.add_column('signals', sa.Column('delta_divergence_detected', sa.Boolean(), nullable=True))
    
    # Agregar campo stop_loss_price a trades
    op.add_column('trades', sa.Column('stop_loss_price', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar campos de trades
    op.drop_column('trades', 'stop_loss_price')
    
    # Eliminar campos de signals
    op.drop_column('signals', 'delta_divergence_detected')
    op.drop_column('signals', 'vpoc_level')
    op.drop_column('signals', 'vwap_value')
    
    # Eliminar campos de strategy_configs
    op.drop_column('strategy_configs', 'lvn_lookback')
    op.drop_column('strategy_configs', 'min_volume_period')
    op.drop_column('strategy_configs', 'volatility_threshold')
    op.drop_column('strategy_configs', 'delta_lookback_vv')
    op.drop_column('strategy_configs', 'value_area_percent')
    op.drop_column('strategy_configs', 'volume_profile_period')
    op.drop_column('strategy_configs', 'vwap_period_days')
