"""
Estrategia Funnel Logic: Lógica Jerárquica con Máquina de Estados.

Implementa una arquitectura de tres etapas secuenciales:
1. Contexto (ESCANEO): EMA 200 para determinar dirección
2. Setup (VIGILANCIA): RSI y Volume Ratio para detectar retrocesos débiles
3. Confirmación (ESPERANDO_CONFIRMACIÓN): Volume Delta para confirmar entrada
"""

import logging
import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .strategy import Strategy
from .exceptions import StrategyError

logger = logging.getLogger(__name__)


class TradingState(str, Enum):
    """Estados de la máquina de estados."""
    ESCANEO = "ESCANEO"  # Buscando dirección del mercado
    VIGILANCIA = "VIGILANCIA"  # Detectando setup de retroceso débil
    ESPERANDO_CONFIRMACION = "ESPERANDO_CONFIRMACION"  # Esperando confirmación de Delta
    EJECUCION = "EJECUCION"  # Señal ejecutada, volver a ESCANEO


class MarketDirection(str, Enum):
    """Dirección del mercado."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class SetupContext:
    """Contexto de un setup detectado."""
    direction: MarketDirection
    entry_index: int
    candles_since_setup: int = 0
    max_wait_candles: int = 5


class FunnelStrategy(Strategy):
    """
    Estrategia Funnel Logic con máquina de estados jerárquica.
    
    Arquitectura:
    1. Etapa 1 (Contexto): EMA 200 determina dirección exclusiva (Long/Short)
    2. Etapa 2 (Setup): RSI < 30 y Volume Ratio < 0.8 detectan retroceso débil
    3. Etapa 3 (Confirmación): Volume Delta positivo confirma entrada
    """
    
    def __init__(
        self,
        ema_period: int = 200,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        volume_period: int = 20,
        volume_ratio_threshold: float = 0.8,
        delta_confirmation_candles: int = 5,
        delta_lookback: int = 3
    ):
        """
        Inicializa la estrategia Funnel Logic.
        
        Args:
            ema_period: Período para EMA de contexto (por defecto 200).
            rsi_period: Período para RSI (por defecto 14).
            rsi_oversold: Umbral RSI para sobreventa (por defecto 30.0).
            rsi_overbought: Umbral RSI para sobrecompra (por defecto 70.0).
            volume_period: Período para calcular promedio de volumen (por defecto 20).
            volume_ratio_threshold: Umbral máximo de Volume Ratio para setup (por defecto 0.8).
            delta_confirmation_candles: Máximo de velas para esperar confirmación (por defecto 5).
            delta_lookback: Velas hacia atrás para analizar Delta (por defecto 3).
        """
        if ema_period < 1:
            raise StrategyError("El período EMA debe ser mayor que 0")
        if rsi_period < 2:
            raise StrategyError("El período RSI debe ser al menos 2")
        if volume_period < 1:
            raise StrategyError("El período de volumen debe ser mayor que 0")
        if delta_confirmation_candles < 1:
            raise StrategyError("El número de velas de confirmación debe ser mayor que 0")
        
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.volume_period = volume_period
        self.volume_ratio_threshold = volume_ratio_threshold
        self.delta_confirmation_candles = delta_confirmation_candles
        self.delta_lookback = delta_lookback
        
        logger.info(
            f"FunnelStrategy inicializada: EMA({ema_period}), RSI({rsi_period}), "
            f"Volume Ratio threshold={volume_ratio_threshold}, Delta confirmation={delta_confirmation_candles} velas"
        )
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calcula la media móvil exponencial."""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calcula el RSI (Relative Strength Index)."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_volume_ratio(self, volume: pd.Series, period: int) -> pd.Series:
        """Calcula el ratio de volumen (volumen actual / promedio)."""
        volume_ma = volume.rolling(window=period).mean()
        return volume / volume_ma
    
    def calculate_volume_delta(self, data: pd.DataFrame) -> pd.Series:
        """
        Calcula Volume Delta aproximado basado en precio y volumen.
        
        Nota: Sin datos de order book, usamos una aproximación:
        - Delta positivo si: precio sube Y volumen alto
        - Delta negativo si: precio baja Y volumen alto
        - Delta neutral si: volumen bajo
        
        Args:
            data: DataFrame con 'close', 'high', 'low', 'volume'.
            
        Returns:
            Series con valores de Delta aproximados.
        """
        close = data['close']
        volume = data['volume']
        
        # Calcular cambio de precio
        price_change = close.diff()
        price_change_pct = price_change / close.shift(1)
        
        # Normalizar volumen (relativo al promedio)
        volume_ma = volume.rolling(window=self.volume_period).mean()
        volume_normalized = volume / volume_ma
        
        # Delta aproximado: dirección del precio * volumen normalizado
        # Si precio sube y volumen alto -> Delta positivo (compra agresiva)
        # Si precio baja y volumen alto -> Delta negativo (venta agresiva)
        delta = price_change_pct * volume_normalized * 1000  # Escalar para mejor visualización
        
        return delta
    
    def check_trend(self, close_price: float, ema_200: float) -> MarketDirection:
        """
        Etapa 1: Filtro de Contexto (ESCANEO).
        
        Determina la dirección exclusiva del mercado basada en EMA 200.
        
        Args:
            close_price: Precio de cierre actual.
            ema_200: Valor de EMA 200.
            
        Returns:
            MarketDirection: LONG, SHORT o NEUTRAL.
        """
        if pd.isna(ema_200):
            return MarketDirection.NEUTRAL
        
        if close_price > ema_200:
            return MarketDirection.LONG
        elif close_price < ema_200:
            return MarketDirection.SHORT
        else:
            return MarketDirection.NEUTRAL
    
    def check_setup(
        self,
        direction: MarketDirection,
        rsi: float,
        volume_ratio: float
    ) -> bool:
        """
        Etapa 2: Filtro de Gatillo/Setup (VIGILANCIA).
        
        Detecta retrocesos débiles en contra de la tendencia principal.
        
        Args:
            direction: Dirección del mercado (LONG o SHORT).
            rsi: Valor RSI actual.
            volume_ratio: Ratio de volumen actual.
            
        Returns:
            True si se detecta un setup válido.
        """
        if pd.isna(rsi) or pd.isna(volume_ratio):
            return False
        
        if direction == MarketDirection.LONG:
            # Para Long: buscar sobreventa (RSI < 30) y volumen bajo (< 0.8)
            return rsi < self.rsi_oversold and volume_ratio < self.volume_ratio_threshold
        
        elif direction == MarketDirection.SHORT:
            # Para Short: buscar sobrecompra (RSI > 70) y volumen bajo (< 0.8)
            return rsi > self.rsi_overbought and volume_ratio < self.volume_ratio_threshold
        
        return False
    
    def check_confirmation(
        self,
        direction: MarketDirection,
        current_delta: float,
        delta_history: pd.Series,
        price_history: pd.Series,
        current_index: int
    ) -> Tuple[bool, str]:
        """
        Etapa 3: Filtro de Confirmación (ESPERANDO_CONFIRMACIÓN).
        
        Confirma entrada cuando hay flujo agresivo a favor de la tendencia.
        
        Args:
            direction: Dirección esperada (LONG o SHORT).
            current_delta: Delta de la vela actual.
            delta_history: Historial de Delta.
            price_history: Historial de precios.
            current_index: Índice actual en el DataFrame.
            
        Returns:
            Tuple (bool, str): (True si confirmado, razón de confirmación).
        """
        if pd.isna(current_delta):
            return False, "Delta no disponible"
        
        # Confirmación 1: Delta se vuelve positivo (para Long) o negativo (para Short)
        if direction == MarketDirection.LONG:
            if current_delta > 0:
                return True, "Delta positivo detectado"
            
            # Confirmación 2: Divergencia de Delta (precio baja, Delta sube)
            if current_index >= self.delta_lookback:
                recent_deltas = delta_history.iloc[current_index - self.delta_lookback:current_index + 1]
                recent_prices = price_history.iloc[current_index - self.delta_lookback:current_index + 1]
                
                # Verificar si Delta está subiendo mientras precio baja
                delta_trend = recent_deltas.iloc[-1] > recent_deltas.iloc[0]
                price_trend = recent_prices.iloc[-1] < recent_prices.iloc[0]
                
                if delta_trend and price_trend:
                    return True, "Divergencia de Delta detectada (precio baja, Delta sube)"
        
        elif direction == MarketDirection.SHORT:
            if current_delta < 0:
                return True, "Delta negativo detectado"
            
            # Confirmación 2: Divergencia de Delta (precio sube, Delta baja)
            if current_index >= self.delta_lookback:
                recent_deltas = delta_history.iloc[current_index - self.delta_lookback:current_index + 1]
                recent_prices = price_history.iloc[current_index - self.delta_lookback:current_index + 1]
                
                # Verificar si Delta está bajando mientras precio sube
                delta_trend = recent_deltas.iloc[-1] < recent_deltas.iloc[0]
                price_trend = recent_prices.iloc[-1] > recent_prices.iloc[0]
                
                if delta_trend and price_trend:
                    return True, "Divergencia de Delta detectada (precio sube, Delta baja)"
        
        return False, "Sin confirmación"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Genera señales usando la máquina de estados Funnel Logic.
        
        Args:
            data: DataFrame con datos históricos (debe incluir 'close', 'high', 'low', 'volume').
            
        Returns:
            Series con señales: 1 (compra), -1 (venta), 0 (mantener).
        """
        try:
            self.validate_data(data)
            
            # Validar columnas requeridas
            required_cols = ['close', 'high', 'low', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                raise StrategyError(f"Faltan columnas requeridas: {missing_cols}")
            
            min_periods = max(self.ema_period, self.rsi_period, self.volume_period)
            if len(data) < min_periods:
                raise StrategyError(
                    f"Se requieren al menos {min_periods} períodos de datos, "
                    f"pero solo hay {len(data)}"
                )
            
            # Calcular indicadores
            close_prices = data['close']
            ema_200 = self.calculate_ema(close_prices, self.ema_period)
            rsi = self.calculate_rsi(close_prices, self.rsi_period)
            volume_ratio = self.calculate_volume_ratio(data['volume'], self.volume_period)
            volume_delta = self.calculate_volume_delta(data)
            
            # Inicializar señales y máquina de estados
            signals = pd.Series(0, index=data.index, dtype=int)
            current_state = TradingState.ESCANEO
            setup_context: Optional[SetupContext] = None
            
            # Procesar cada vela
            for i in range(min_periods, len(signals)):
                current_price = close_prices.iloc[i]
                current_ema = ema_200.iloc[i]
                current_rsi = rsi.iloc[i]
                current_volume_ratio = volume_ratio.iloc[i]
                current_delta = volume_delta.iloc[i]
                
                # Máquina de estados
                if current_state == TradingState.ESCANEO:
                    # Etapa 1: Determinar dirección del mercado
                    direction = self.check_trend(current_price, current_ema)
                    
                    if direction != MarketDirection.NEUTRAL:
                        # Cambiar a estado de vigilancia
                        current_state = TradingState.VIGILANCIA
                        logger.debug(f"Vela {i}: Cambio a VIGILANCIA, dirección={direction.value}")
                
                elif current_state == TradingState.VIGILANCIA:
                    # Etapa 2: Buscar setup de retroceso débil
                    direction = self.check_trend(current_price, current_ema)
                    
                    if direction != MarketDirection.NEUTRAL:
                        setup_detected = self.check_setup(direction, current_rsi, current_volume_ratio)
                        
                        if setup_detected:
                            # Setup detectado, cambiar a espera de confirmación
                            setup_context = SetupContext(
                                direction=direction,
                                entry_index=i,
                                candles_since_setup=0,
                                max_wait_candles=self.delta_confirmation_candles
                            )
                            current_state = TradingState.ESPERANDO_CONFIRMACION
                            logger.debug(
                                f"Vela {i}: Setup detectado para {direction.value}, "
                                f"RSI={current_rsi:.2f}, Volume Ratio={current_volume_ratio:.2f}"
                            )
                    else:
                        # Perdimos la dirección, volver a escaneo
                        current_state = TradingState.ESCANEO
                
                elif current_state == TradingState.ESPERANDO_CONFIRMACION:
                    if setup_context is None:
                        current_state = TradingState.ESCANEO
                        continue
                    
                    # Incrementar contador de velas
                    setup_context.candles_since_setup += 1
                    
                    # Verificar confirmación de Delta
                    confirmed, reason = self.check_confirmation(
                        setup_context.direction,
                        current_delta,
                        volume_delta,
                        close_prices,
                        i
                    )
                    
                    if confirmed:
                        # Confirmación recibida, ejecutar señal
                        if setup_context.direction == MarketDirection.LONG:
                            signals.iloc[i] = 1
                            logger.info(
                                f"Vela {i}: SEÑAL LONG ejecutada. Razón: {reason}, "
                                f"Delta={current_delta:.2f}"
                            )
                        elif setup_context.direction == MarketDirection.SHORT:
                            signals.iloc[i] = -1
                            logger.info(
                                f"Vela {i}: SEÑAL SHORT ejecutada. Razón: {reason}, "
                                f"Delta={current_delta:.2f}"
                            )
                        
                        # Resetear a escaneo
                        current_state = TradingState.ESCANEO
                        setup_context = None
                    
                    elif setup_context.candles_since_setup >= setup_context.max_wait_candles:
                        # Timeout: cancelar setup y volver a escaneo
                        logger.debug(
                            f"Vela {i}: Timeout de confirmación después de "
                            f"{setup_context.candles_since_setup} velas"
                        )
                        current_state = TradingState.ESCANEO
                        setup_context = None
                    
                    # Verificar si perdimos la dirección del mercado
                    else:
                        current_direction = self.check_trend(current_price, current_ema)
                        if current_direction != setup_context.direction:
                            logger.debug(
                                f"Vela {i}: Cambio de dirección del mercado, cancelando setup"
                            )
                            current_state = TradingState.ESCANEO
                            setup_context = None
                
                elif current_state == TradingState.EJECUCION:
                    # Después de ejecutar, volver a escaneo
                    current_state = TradingState.ESCANEO
            
            # Log de estadísticas
            buy_signals = (signals == 1).sum()
            sell_signals = (signals == -1).sum()
            logger.info(
                f"FunnelStrategy: {buy_signals} señales LONG, {sell_signals} señales SHORT generadas"
            )
            
            return signals
            
        except StrategyError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado al generar señales: {e}")
            raise StrategyError(f"Error al generar señales: {e}")
    
    def get_params(self) -> Dict[str, Any]:
        """Retorna los parámetros de la estrategia."""
        return {
            'strategy_type': 'Funnel Logic',
            'ema_period': self.ema_period,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'volume_period': self.volume_period,
            'volume_ratio_threshold': self.volume_ratio_threshold,
            'delta_confirmation_candles': self.delta_confirmation_candles,
            'delta_lookback': self.delta_lookback
        }
