"""
Módulo de excepciones personalizadas para el sistema de trading.

Este módulo centraliza todas las excepciones personalizadas del sistema.
"""


class TradingBotError(Exception):
    """Excepción base para todos los errores del sistema de trading."""
    pass


class DataHandlerError(TradingBotError):
    """Excepción para errores relacionados con el manejo de datos."""
    pass


class StrategyError(TradingBotError):
    """Excepción para errores relacionados con estrategias."""
    pass


class BacktesterError(TradingBotError):
    """Excepción para errores relacionados con el backtesting."""
    pass
