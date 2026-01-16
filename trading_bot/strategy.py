"""
Módulo Strategy: Define la interfaz y implementaciones de estrategias de trading.

Este módulo proporciona una clase base Strategy y la implementación SMACrossover
para estrategias de cruce de medias móviles.
"""

import logging
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any

from .exceptions import StrategyError


logger = logging.getLogger(__name__)


class Strategy(ABC):
    """
    Clase abstracta base para estrategias de trading.
    
    Todas las estrategias deben heredar de esta clase e implementar
    los métodos abstractos generate_signals y get_params.
    """
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Genera señales de trading basadas en los datos.
        
        Args:
            data: DataFrame con datos históricos (debe incluir 'close').
            
        Returns:
            Series con señales: 1 (compra), -1 (venta), 0 (mantener).
            
        Raises:
            StrategyError: Si hay error al generar señales.
        """
        pass
    
    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """
        Retorna los parámetros de la estrategia.
        
        Returns:
            Diccionario con los parámetros de la estrategia.
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Valida que los datos sean adecuados para la estrategia.
        
        Args:
            data: DataFrame a validar.
            
        Returns:
            True si los datos son válidos.
            
        Raises:
            StrategyError: Si los datos no son válidos.
        """
        if data.empty:
            raise StrategyError("El DataFrame está vacío")
        
        if 'close' not in data.columns:
            raise StrategyError("El DataFrame debe contener la columna 'close'")
        
        if len(data) < 2:
            raise StrategyError("Se requieren al menos 2 períodos de datos")
        
        return True


class SMACrossover(Strategy):
    """
    Estrategia de cruce de medias móviles (SMA o EMA).
    
    Genera señales de compra cuando la media rápida cruza por encima de la lenta,
    y señales de venta cuando cruza por debajo.
    
    Attributes:
        fast_period (int): Período para la media móvil rápida.
        slow_period (int): Período para la media móvil lenta.
        use_ema (bool): Si True usa EMA, si False usa SMA (por defecto False).
        rsi_period (int): Período para RSI como filtro (None para desactivar).
        rsi_overbought (float): Umbral RSI para sobrecompra (por defecto 70).
        rsi_oversold (float): Umbral RSI para sobreventa (por defecto 30).
        trend_filter_period (int): Período para SMA de tendencia (None para desactivar).
    """
    
    def __init__(
        self,
        fast_period: int = 50,
        slow_period: int = 200,
        use_ema: bool = False,
        rsi_period: int = None,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        trend_filter_period: int = None,
        volume_period: int = None,
        volume_ratio_threshold: float = None,
        atr_period: int = None,
        atr_multiplier: float = None,
        market_regime_enabled: bool = False,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        max_volatility_multiplier: float = None
    ):
        """
        Inicializa la estrategia SMACrossover.
        
        Args:
            fast_period: Período para la media móvil rápida (por defecto 50).
            slow_period: Período para la media móvil lenta (por defecto 200).
            use_ema: Si True usa EMA en lugar de SMA (por defecto False).
            rsi_period: Período para RSI como filtro (None para desactivar).
            rsi_overbought: Umbral RSI para considerar sobrecompra (por defecto 70).
            rsi_oversold: Umbral RSI para considerar sobreventa (por defecto 30).
            trend_filter_period: Período para SMA de tendencia (None para desactivar).
            volume_period: Período para calcular volumen promedio (None para desactivar).
            volume_ratio_threshold: Ratio mínimo de volumen (volumen_actual/promedio) para filtrar señales (None para desactivar).
            atr_period: Período para calcular ATR (None para desactivar).
            atr_multiplier: Multiplicador de ATR para stops dinámicos (None para desactivar).
            market_regime_enabled: Si True, habilita filtro de regímenes de mercado (por defecto False).
            adx_period: Período para calcular ADX (por defecto 14).
            adx_threshold: Umbral ADX para considerar tendencia fuerte (por defecto 25.0).
            max_volatility_multiplier: Multiplicador máximo de ATR para filtrar alta volatilidad (None para desactivar).
            
        Raises:
            StrategyError: Si los parámetros no son válidos.
        """
        if fast_period >= slow_period:
            raise StrategyError("El período rápido debe ser menor que el lento")
        
        if fast_period < 1 or slow_period < 1:
            raise StrategyError("Los períodos deben ser mayores que 0")
        
        if rsi_period is not None and rsi_period < 2:
            raise StrategyError("El período RSI debe ser al menos 2")
        
        if trend_filter_period is not None and trend_filter_period < 1:
            raise StrategyError("El período del filtro de tendencia debe ser mayor que 0")
        
        if volume_period is not None and volume_period < 1:
            raise StrategyError("El período de volumen debe ser mayor que 0")
        
        if volume_ratio_threshold is not None and volume_ratio_threshold < 0:
            raise StrategyError("El umbral de ratio de volumen debe ser mayor o igual a 0")
        
        if (volume_period is None) != (volume_ratio_threshold is None):
            raise StrategyError("volume_period y volume_ratio_threshold deben estar ambos activados o ambos desactivados")
        
        if atr_period is not None and atr_period < 1:
            raise StrategyError("El período ATR debe ser mayor que 0")
        
        if atr_multiplier is not None and atr_multiplier <= 0:
            raise StrategyError("El multiplicador ATR debe ser mayor que 0")
        
        if (atr_period is None) != (atr_multiplier is None):
            raise StrategyError("atr_period y atr_multiplier deben estar ambos activados o ambos desactivados")
        
        if adx_period < 2:
            raise StrategyError("El período ADX debe ser al menos 2")
        
        if adx_threshold < 0 or adx_threshold > 100:
            raise StrategyError("El umbral ADX debe estar entre 0 y 100")
        
        if max_volatility_multiplier is not None and max_volatility_multiplier <= 0:
            raise StrategyError("El multiplicador máximo de volatilidad debe ser mayor que 0")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.use_ema = use_ema
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.trend_filter_period = trend_filter_period
        self.volume_period = volume_period
        self.volume_ratio_threshold = volume_ratio_threshold
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.market_regime_enabled = market_regime_enabled
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.max_volatility_multiplier = max_volatility_multiplier
        
        ma_type = "EMA" if use_ema else "SMA"
        rsi_info = f", RSI({rsi_period})" if rsi_period else ""
        trend_info = f", Trend SMA({trend_filter_period})" if trend_filter_period else ""
        volume_info = f", Volume Ratio({volume_period}, threshold={volume_ratio_threshold})" if volume_period else ""
        atr_info = f", ATR({atr_period}, multiplier={atr_multiplier})" if atr_period else ""
        regime_info = f", Market Regime (ADX={adx_period}, threshold={adx_threshold})" if market_regime_enabled else ""
        logger.info(f"SMACrossover inicializada: {ma_type} fast={fast_period}, slow={slow_period}{rsi_info}{trend_info}{volume_info}{atr_info}{regime_info}")
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calcula la media móvil simple.
        
        Args:
            data: Series con los precios de cierre.
            period: Período para la media móvil.
            
        Returns:
            Series con la media móvil calculada.
        """
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calcula la media móvil exponencial.
        
        Args:
            data: Series con los precios de cierre.
            period: Período para la media móvil.
            
        Returns:
            Series con la media móvil exponencial calculada.
        """
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula el RSI (Relative Strength Index).
        
        Args:
            data: Series con los precios de cierre.
            period: Período para el cálculo del RSI (por defecto 14).
            
        Returns:
            Series con los valores del RSI.
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula el ATR (Average True Range).
        
        Args:
            high: Series con los precios máximos.
            low: Series con los precios mínimos.
            close: Series con los precios de cierre.
            period: Período para el cálculo del ATR (por defecto 14).
            
        Returns:
            Series con los valores del ATR.
        """
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula el ADX (Average Directional Index).
        
        Args:
            high: Series con los precios máximos.
            low: Series con los precios mínimos.
            close: Series con los precios de cierre.
            period: Período para el cálculo del ADX (por defecto 14).
            
        Returns:
            Series con los valores del ADX.
        """
        # Calcular +DM y -DM
        high_diff = high.diff()
        low_diff = -low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Calcular True Range
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        # Suavizar +DM, -DM y TR
        atr = true_range.rolling(window=period).mean()
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        
        # Calcular DI+ y DI-
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # Calcular DX (evitar división por cero)
        di_sum = plus_di + minus_di
        dx = pd.Series(index=di_sum.index, dtype=float)
        dx[di_sum != 0] = 100 * np.abs(plus_di[di_sum != 0] - minus_di[di_sum != 0]) / di_sum[di_sum != 0]
        dx[di_sum == 0] = 0
        
        # Calcular ADX (media móvil de DX)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Genera señales de trading basadas en el cruce de medias móviles.
        
        Args:
            data: DataFrame con datos históricos (debe incluir 'close').
            
        Returns:
            Series con señales: 1 (compra), -1 (venta), 0 (mantener).
            
        Raises:
            StrategyError: Si hay error al generar señales.
        """
        try:
            self.validate_data(data)
            
            if len(data) < self.slow_period:
                raise StrategyError(
                    f"Se requieren al menos {self.slow_period} períodos de datos, "
                    f"pero solo hay {len(data)}"
                )
            
            close_prices = data['close']
            
            # Calcular medias móviles (SMA o EMA)
            if self.use_ema:
                ma_fast = self.calculate_ema(close_prices, self.fast_period)
                ma_slow = self.calculate_ema(close_prices, self.slow_period)
            else:
                ma_fast = self.calculate_sma(close_prices, self.fast_period)
                ma_slow = self.calculate_sma(close_prices, self.slow_period)
            
            # Calcular RSI si está habilitado
            rsi = None
            if self.rsi_period is not None:
                if len(data) < self.rsi_period:
                    logger.warning(f"RSI requiere al menos {self.rsi_period} períodos, desactivando filtro RSI")
                else:
                    rsi = self.calculate_rsi(close_prices, self.rsi_period)
            
            # Calcular SMA de tendencia si está habilitado
            trend_sma = None
            if self.trend_filter_period is not None:
                if len(data) < self.trend_filter_period:
                    logger.warning(f"Filtro de tendencia requiere al menos {self.trend_filter_period} períodos, desactivando filtro")
                else:
                    trend_sma = self.calculate_sma(close_prices, self.trend_filter_period)
            
            # Calcular Volume Ratio si está habilitado
            volume_ratio = None
            if self.volume_period is not None and self.volume_ratio_threshold is not None:
                if 'volume' not in data.columns:
                    logger.warning("Columna 'volume' no disponible, desactivando filtro de volumen")
                elif len(data) < self.volume_period:
                    logger.warning(f"Filtro de volumen requiere al menos {self.volume_period} períodos, desactivando filtro")
                else:
                    volume_ma = data['volume'].rolling(window=self.volume_period).mean()
                    volume_ratio = data['volume'] / volume_ma
            
            # Calcular ATR si está habilitado (para filtro de regímenes)
            atr = None
            atr_values = None
            if self.market_regime_enabled or self.atr_period is not None:
                if not all(col in data.columns for col in ['high', 'low', 'close']):
                    logger.warning("Columnas 'high', 'low', 'close' requeridas para ATR, desactivando")
                else:
                    atr_period = self.atr_period if self.atr_period else 14
                    if len(data) < atr_period:
                        logger.warning(f"ATR requiere al menos {atr_period} períodos, desactivando")
                    else:
                        atr = self.calculate_atr(data['high'], data['low'], data['close'], atr_period)
                        atr_values = atr  # Almacenar para uso posterior
            
            # Calcular ADX si el filtro de regímenes está habilitado
            adx = None
            if self.market_regime_enabled:
                if not all(col in data.columns for col in ['high', 'low', 'close']):
                    logger.warning("Columnas 'high', 'low', 'close' requeridas para ADX, desactivando filtro de regímenes")
                else:
                    if len(data) < self.adx_period:
                        logger.warning(f"ADX requiere al menos {self.adx_period} períodos, desactivando filtro de regímenes")
                    else:
                        adx = self.calculate_adx(data['high'], data['low'], data['close'], self.adx_period)
            
            # Inicializar señales
            signals = pd.Series(0, index=data.index, dtype=int)
            
            # Detectar cruces con filtros opcionales
            for i in range(1, len(signals)):
                # Verificar cruce alcista (compra)
                crossover_bullish = (ma_fast.iloc[i] > ma_slow.iloc[i] and 
                                     ma_fast.iloc[i-1] <= ma_slow.iloc[i-1])
                
                # Verificar cruce bajista (venta)
                crossover_bearish = (ma_fast.iloc[i] < ma_slow.iloc[i] and 
                                     ma_fast.iloc[i-1] >= ma_slow.iloc[i-1])
                
                # Aplicar filtro RSI si está habilitado
                rsi_filter_buy = True
                rsi_filter_sell = True
                
                if rsi is not None and not pd.isna(rsi.iloc[i]):
                    # Para compra: RSI no debe estar en sobrecompra
                    rsi_filter_buy = rsi.iloc[i] < self.rsi_overbought
                    # Para venta: RSI no debe estar en sobreventa
                    rsi_filter_sell = rsi.iloc[i] > self.rsi_oversold
                
                # Aplicar filtro de tendencia si está habilitado
                trend_filter_buy = True
                trend_filter_sell = True
                
                if trend_sma is not None and not pd.isna(trend_sma.iloc[i]):
                    price = close_prices.iloc[i]
                    # Para compra: precio debe estar por encima de la SMA de tendencia
                    trend_filter_buy = price > trend_sma.iloc[i]
                    # Para venta: precio debe estar por debajo de la SMA de tendencia
                    trend_filter_sell = price < trend_sma.iloc[i]
                
                # Aplicar filtro de volumen (Volume Ratio) si está habilitado
                volume_filter_buy = True
                volume_filter_sell = True
                
                if volume_ratio is not None and not pd.isna(volume_ratio.iloc[i]):
                    # Solo ejecutar señales si el volumen está por encima del threshold
                    volume_filter_buy = volume_ratio.iloc[i] >= self.volume_ratio_threshold
                    volume_filter_sell = volume_ratio.iloc[i] >= self.volume_ratio_threshold
                
                # Aplicar filtro de regímenes de mercado si está habilitado
                regime_filter = True
                if self.market_regime_enabled:
                    if adx is not None and atr is not None and not pd.isna(adx.iloc[i]) and not pd.isna(atr.iloc[i]):
                        current_adx = adx.iloc[i]
                        current_atr = atr.iloc[i]
                        price = close_prices.iloc[i]
                        
                        # Filtro 1: ADX debe indicar tendencia fuerte (ADX > threshold)
                        strong_trend = current_adx >= self.adx_threshold
                        
                        # Filtro 2: Verificar alta volatilidad (ATR relativo al precio)
                        high_volatility = False
                        if self.max_volatility_multiplier is not None:
                            # Calcular ATR promedio para comparar
                            if i >= (self.atr_period if self.atr_period else 14):
                                atr_avg = atr.iloc[i - (self.atr_period if self.atr_period else 14):i].mean()
                                # Si ATR actual es mucho mayor que el promedio, es alta volatilidad
                                if atr_avg > 0:
                                    atr_ratio = current_atr / atr_avg
                                    high_volatility = atr_ratio > self.max_volatility_multiplier
                        
                        # Solo permitir señales si hay tendencia fuerte Y no hay alta volatilidad extrema
                        regime_filter = strong_trend and not high_volatility
                    else:
                        # Si no se pueden calcular indicadores, permitir señales (fallback)
                        regime_filter = True
                
                # Señal de compra: cruce alcista + filtro RSI + filtro de tendencia + filtro de volumen + filtro de regímenes
                if crossover_bullish and rsi_filter_buy and trend_filter_buy and volume_filter_buy and regime_filter:
                    signals.iloc[i] = 1
                
                # Señal de venta: cruce bajista + filtro RSI + filtro de tendencia + filtro de volumen + filtro de regímenes
                elif crossover_bearish and rsi_filter_sell and trend_filter_sell and volume_filter_sell and regime_filter:
                    signals.iloc[i] = -1
            
            # Log de estadísticas
            buy_signals = (signals == 1).sum()
            sell_signals = (signals == -1).sum()
            logger.info(f"Señales generadas: {buy_signals} compras, {sell_signals} ventas")
            
            return signals
            
        except StrategyError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado al generar señales: {e}")
            raise StrategyError(f"Error al generar señales: {e}")
    
    def get_params(self) -> Dict[str, Any]:
        """
        Retorna los parámetros de la estrategia.
        
        Returns:
            Diccionario con los parámetros de la estrategia.
        """
        params = {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'use_ema': self.use_ema,
            'strategy_type': 'EMA Crossover' if self.use_ema else 'SMA Crossover'
        }
        if self.rsi_period is not None:
            params['rsi_period'] = self.rsi_period
            params['rsi_overbought'] = self.rsi_overbought
            params['rsi_oversold'] = self.rsi_oversold
        if self.trend_filter_period is not None:
            params['trend_filter_period'] = self.trend_filter_period
        if self.volume_period is not None:
            params['volume_period'] = self.volume_period
            params['volume_ratio_threshold'] = self.volume_ratio_threshold
        if self.atr_period is not None:
            params['atr_period'] = self.atr_period
            params['atr_multiplier'] = self.atr_multiplier
        if self.market_regime_enabled:
            params['market_regime_enabled'] = True
            params['adx_period'] = self.adx_period
            params['adx_threshold'] = self.adx_threshold
            if self.max_volatility_multiplier is not None:
                params['max_volatility_multiplier'] = self.max_volatility_multiplier
        return params
