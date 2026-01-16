"""
Trading Bot: Sistema modular para backtesting de estrategias de trading algorítmico.

Este paquete proporciona herramientas para descargar datos históricos,
implementar estrategias de trading y realizar backtesting con cálculo de métricas.
"""

from .data_handler import DataHandler, DataHandlerError
from .strategy import Strategy, SMACrossover, StrategyError
from .funnel_strategy import FunnelStrategy
from .volume_value_strategy import VolumeValueStrategy
from .backtester import Backtester, BacktesterError
from .strategy_registry import StrategyRegistry, register_strategy

# Registrar estrategias disponibles
StrategyRegistry.register(
    'SMA_CROSSOVER',
    SMACrossover,
    display_name='SMA Crossover',
    description='Estrategia de cruce de medias móviles (SMA/EMA) con filtros opcionales'
)

StrategyRegistry.register(
    'FUNNEL_LOGIC',
    FunnelStrategy,
    display_name='Funnel Logic',
    description='Estrategia jerárquica en 3 etapas: Contexto, Setup y Confirmación'
)

StrategyRegistry.register(
    'VOLUME_VALUE',
    VolumeValueStrategy,
    display_name='Volume Value Strategy',
    description='Estrategia basada en Auction Market Theory (AMT) y análisis de flujo de órdenes'
)

__version__ = '1.0.0'
__all__ = [
    'DataHandler',
    'DataHandlerError',
    'Strategy',
    'SMACrossover',
    'FunnelStrategy',
    'VolumeValueStrategy',
    'StrategyError',
    'Backtester',
    'BacktesterError',
    'StrategyRegistry',
    'register_strategy'
]
