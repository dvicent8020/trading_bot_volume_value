"""
Sistema de Registro de Estrategias - Strategy Registry Pattern.

Permite registrar y recuperar estrategias de trading de forma dinámica.
Facilita la extensión del sistema con nuevas estrategias sin modificar código existente.
"""

import logging
from typing import Dict, Type, Optional, Any
from abc import ABC
from .strategy import Strategy
from .exceptions import StrategyError

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Registro centralizado de estrategias de trading.
    
    Implementa el patrón Registry para permitir registro dinámico de estrategias.
    Permite agregar nuevas estrategias sin modificar código existente.
    """
    
    _strategies: Dict[str, Type[Strategy]] = {}
    _strategy_names: Dict[str, str] = {}  # Código -> Nombre legible
    _strategy_descriptions: Dict[str, str] = {}  # Código -> Descripción
    
    @classmethod
    def register(
        cls,
        strategy_code: str,
        strategy_class: Type[Strategy],
        display_name: str = None,
        description: str = ""
    ):
        """
        Registra una estrategia en el registro.
        
        Args:
            strategy_code: Código único de la estrategia (ej: 'sma_crossover', 'funnel_logic')
            strategy_class: Clase de la estrategia (debe heredar de Strategy)
            display_name: Nombre legible para mostrar en UI (opcional)
            description: Descripción de la estrategia (opcional)
        
        Raises:
            StrategyError: Si la clase no hereda de Strategy o el código ya existe.
        """
        if not issubclass(strategy_class, Strategy):
            raise StrategyError(
                f"La clase {strategy_class.__name__} debe heredar de Strategy"
            )
        
        if strategy_code in cls._strategies:
            logger.warning(f"Estrategia '{strategy_code}' ya registrada, sobrescribiendo")
        
        cls._strategies[strategy_code] = strategy_class
        cls._strategy_names[strategy_code] = display_name or strategy_class.__name__
        cls._strategy_descriptions[strategy_code] = description
        
        logger.info(
            f"Estrategia '{strategy_code}' ({display_name or strategy_class.__name__}) "
            f"registrada exitosamente"
        )
    
    @classmethod
    def get_strategy_class(cls, strategy_code: str) -> Type[Strategy]:
        """
        Obtiene la clase de una estrategia registrada.
        
        Args:
            strategy_code: Código de la estrategia a recuperar.
            
        Returns:
            Clase de la estrategia.
            
        Raises:
            StrategyError: Si la estrategia no está registrada.
        """
        if strategy_code not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise StrategyError(
                f"Estrategia '{strategy_code}' no encontrada. "
                f"Estrategias disponibles: {available}"
            )
        
        return cls._strategies[strategy_code]
    
    @classmethod
    def create_strategy(cls, strategy_code: str, **kwargs) -> Strategy:
        """
        Crea una instancia de la estrategia especificada.
        
        Args:
            strategy_code: Código de la estrategia.
            **kwargs: Parámetros para inicializar la estrategia.
            
        Returns:
            Instancia de la estrategia.
            
        Raises:
            StrategyError: Si la estrategia no está registrada o hay error al crearla.
        """
        strategy_class = cls.get_strategy_class(strategy_code)
        
        try:
            return strategy_class(**kwargs)
        except Exception as e:
            raise StrategyError(
                f"Error al crear estrategia '{strategy_code}': {e}"
            ) from e
    
    @classmethod
    def list_strategies(cls) -> Dict[str, Dict[str, str]]:
        """
        Lista todas las estrategias registradas.
        
        Returns:
            Diccionario con información de todas las estrategias registradas.
            Formato: {codigo: {'name': nombre, 'description': descripcion}}
        """
        return {
            code: {
                'name': cls._strategy_names.get(code, code),
                'description': cls._strategy_descriptions.get(code, ''),
                'class_name': cls._strategies[code].__name__
            }
            for code in cls._strategies.keys()
        }
    
    @classmethod
    def is_registered(cls, strategy_code: str) -> bool:
        """
        Verifica si una estrategia está registrada.
        
        Args:
            strategy_code: Código de la estrategia.
            
        Returns:
            True si la estrategia está registrada, False en caso contrario.
        """
        return strategy_code in cls._strategies
    
    @classmethod
    def get_required_params(cls, strategy_code: str) -> Dict[str, Any]:
        """
        Obtiene los parámetros requeridos para una estrategia.
        
        Args:
            strategy_code: Código de la estrategia.
            
        Returns:
            Diccionario con información de parámetros requeridos.
            Por ahora retorna un diccionario básico. Se puede extender con inspección.
        """
        # Por ahora retornamos info básica. Se puede mejorar con inspección de parámetros.
        strategy_class = cls.get_strategy_class(strategy_code)
        
        # Intentar obtener parámetros desde la clase si tiene método estático
        if hasattr(strategy_class, 'get_param_info'):
            return strategy_class.get_param_info()
        
        # Retornar info básica basada en el nombre de la estrategia
        return {
            'strategy_code': strategy_code,
            'class_name': strategy_class.__name__
        }


# Función de conveniencia para registro automático
def register_strategy(
    strategy_code: str,
    display_name: str = None,
    description: str = ""
):
    """
    Decorador para registrar automáticamente una estrategia.
    
    Uso:
        @register_strategy('sma_crossover', 'SMA Crossover', 'Estrategia de cruce de medias')
        class SMACrossover(Strategy):
            ...
    """
    def decorator(strategy_class: Type[Strategy]):
        StrategyRegistry.register(strategy_code, strategy_class, display_name, description)
        return strategy_class
    return decorator
