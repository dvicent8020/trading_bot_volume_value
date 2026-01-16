"""add_strategy_type_and_funnel_logic

Revision ID: 20260114224810
Revises: 19918569ac5d
Create Date: 2026-01-14 22:48:10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260114224810'
down_revision: Union[str, Sequence[str], None] = '19918569ac5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar campo strategy_type
    op.add_column('strategy_configs', sa.Column('strategy_type', sa.String(50), nullable=False, server_default='SMA_CROSSOVER'))
    
    # Hacer campos SMA Crossover opcionales (ahora pueden ser NULL)
    op.alter_column('strategy_configs', 'fast_period', nullable=True)
    op.alter_column('strategy_configs', 'slow_period', nullable=True)
    op.alter_column('strategy_configs', 'use_ema', nullable=True)
    
    # Agregar campos específicos de Funnel Logic
    op.add_column('strategy_configs', sa.Column('ema_period', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('delta_confirmation_candles', sa.Integer(), nullable=True))
    op.add_column('strategy_configs', sa.Column('delta_lookback', sa.Integer(), nullable=True))
    
    # Crear índice en strategy_type para búsquedas rápidas
    op.create_index('idx_strategy_configs_strategy_type', 'strategy_configs', ['strategy_type'])


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar índice
    op.drop_index('idx_strategy_configs_strategy_type', table_name='strategy_configs')
    
    # Eliminar campos Funnel Logic
    op.drop_column('strategy_configs', 'delta_lookback')
    op.drop_column('strategy_configs', 'delta_confirmation_candles')
    op.drop_column('strategy_configs', 'ema_period')
    
    # Restaurar campos SMA Crossover como obligatorios
    # Nota: Esto puede fallar si hay NULLs. En producción, primero actualizar NULLs a valores por defecto
    op.alter_column('strategy_configs', 'use_ema', nullable=False, server_default='false')
    op.alter_column('strategy_configs', 'slow_period', nullable=False)
    op.alter_column('strategy_configs', 'fast_period', nullable=False)
    
    # Eliminar campo strategy_type
    op.drop_column('strategy_configs', 'strategy_type')
