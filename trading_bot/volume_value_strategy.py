"""
VolumeValueStrategy: Estrategia basada en Auction Market Theory (AMT).

Implementa análisis de flujo de órdenes y perfil de volumen sin indicadores
de precio retrasados (RSI, MACD, etc.).

Indicadores:
- VWAP (Volume Weighted Average Price) - Rolling semanal
- Volume Profile (VPOC, VAH, VAL, LVN)
- CVD (Cumulative Volume Delta)
- Detección de divergencias de absorción
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .strategy import Strategy
from .exceptions import StrategyError

logger = logging.getLogger(__name__)


class VolumeValueStrategy(Strategy):
    """
    Estrategia basada en Auction Market Theory y análisis de flujo de órdenes.
    
    Características:
    - Sin indicadores de precio retrasados
    - Basada en volumen y flujo de órdenes
    - Dynamic Stop Loss basado en LVN
    - Filtro de volatilidad climática
    """
    
    def __init__(
        self,
        vwap_period_days: int = 7,  # Período para VWAP (semanal para 4H)
        volume_profile_period: int = 7,  # Período para Volume Profile
        value_area_percent: float = 0.68,  # 68% del volumen (estándar AMT)
        delta_lookback: int = 20,  # Período para calcular CVD
        volatility_threshold: float = 3.0,  # 300% del promedio de volumen
        min_volume_period: int = 20,  # Período para promedio de volumen
        lvn_lookback: int = 50,  # Período para detectar LVN
        market_regime_enabled: bool = False,  # Filtro ADX para regímenes de mercado
        adx_period: int = 14,  # Período para calcular ADX
        adx_threshold: float = 25.0,  # Umbral ADX para tendencia fuerte
        # Mejoras críticas: Filtros de calidad de señales
        signal_cooldown: int = 5,  # Número de velas entre señales
        min_signal_strength: float = 0.5,  # Score mínimo para aceptar señal (0.0-1.0)
        volume_confirmation_enabled: bool = True,  # Habilitar confirmación de volumen
        volume_confirmation_ratio: float = 1.5,  # Ratio mínimo de volumen de dirección
        # Mejoras críticas: Filtros diferenciados LONG vs SHORT
        adx_threshold_long: float = None,  # ADX threshold para LONGs (si None, usa adx_threshold)
        adx_threshold_short: float = None,  # ADX threshold para SHORTs (si None, usa adx_threshold)
        long_filters_enabled: bool = True,  # Habilitar filtros adicionales para LONGs
        disable_longs_if_poor_performance: bool = False,  # Desactivar LONGs si win rate < 30%
        min_long_volume_ratio: float = 1.5,  # Volumen compra debe ser >150% del promedio para LONGs
        # Nuevos filtros de mejora
        disable_longs: bool = False,  # Deshabilitar completamente señales LONG
        disable_shorts: bool = False,  # Deshabilitar completamente señales SHORT
        trend_filter_period: int = 50,  # Período para calcular tendencia mayor (SMA)
        require_uptrend_for_longs: bool = False  # Solo permitir LONGs si precio > SMA(trend_filter_period)
    ):
        """
        Inicializa la estrategia VolumeValueStrategy.
        
        Args:
            vwap_period_days: Días para calcular VWAP rolling (default: 7 para semanal).
            volume_profile_period: Período para calcular Volume Profile (default: 7 días).
            value_area_percent: Porcentaje de volumen para Value Area (default: 0.68 = 68%).
            delta_lookback: Período para calcular CVD (default: 20 velas).
            volatility_threshold: Multiplicador de volumen para filtrar volatilidad climática (default: 3.0 = 300%).
            min_volume_period: Período para calcular promedio de volumen (default: 20).
            lvn_lookback: Período para detectar LVN (default: 50 velas).
        """
        if vwap_period_days < 1:
            raise StrategyError("vwap_period_days debe ser mayor que 0")
        if not 0 < value_area_percent < 1:
            raise StrategyError("value_area_percent debe estar entre 0 y 1")
        if volatility_threshold < 1.0:
            raise StrategyError("volatility_threshold debe ser >= 1.0")
        
        self.vwap_period_days = vwap_period_days
        self.volume_profile_period = volume_profile_period
        self.value_area_percent = value_area_percent
        self.delta_lookback = delta_lookback
        self.volatility_threshold = volatility_threshold
        self.min_volume_period = min_volume_period
        self.lvn_lookback = lvn_lookback
        self.market_regime_enabled = market_regime_enabled
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        
        # Mejoras críticas: Filtros de calidad
        self.signal_cooldown = signal_cooldown
        self.min_signal_strength = min_signal_strength
        self.volume_confirmation_enabled = volume_confirmation_enabled
        self.volume_confirmation_ratio = volume_confirmation_ratio
        
        # Mejoras críticas: Filtros diferenciados
        self.adx_threshold_long = adx_threshold_long if adx_threshold_long is not None else adx_threshold
        self.adx_threshold_short = adx_threshold_short if adx_threshold_short is not None else adx_threshold
        self.long_filters_enabled = long_filters_enabled
        self.disable_longs_if_poor_performance = disable_longs_if_poor_performance
        self.min_long_volume_ratio = min_long_volume_ratio
        
        # Nuevos filtros de mejora
        self.disable_longs = disable_longs
        self.disable_shorts = disable_shorts
        self.trend_filter_period = trend_filter_period
        self.require_uptrend_for_longs = require_uptrend_for_longs
        
        logger.info(
            f"VolumeValueStrategy inicializada: VWAP={vwap_period_days}d, "
            f"VP={volume_profile_period}d, Value Area={value_area_percent*100}%, "
            f"Volatility Threshold={volatility_threshold*100}%, "
            f"ADX Filter={'ON' if market_regime_enabled else 'OFF'}, "
            f"Signal Cooldown={signal_cooldown}, Min Strength={min_signal_strength}"
        )
    
    def calculate_rolling_vwap(
        self,
        data: pd.DataFrame,
        period_days: int,
        timeframe: str = '4h'
    ) -> pd.Series:
        """
        Calcula VWAP rolling con reinicio semanal.
        
        Args:
            data: DataFrame con 'close', 'high', 'low', 'volume', 'timestamp' o índice datetime.
            period_days: Días para el período de VWAP.
            timeframe: Timeframe de las velas (para calcular reinicios).
            
        Returns:
            Series con valores de VWAP.
        """
        if 'volume' not in data.columns or 'close' not in data.columns:
            raise StrategyError("Datos deben incluir 'close' y 'volume'")
        
        # Asegurar que el índice es datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
            else:
                raise StrategyError("Datos deben tener índice datetime o columna 'timestamp'")
        
        # Calcular VWAP rolling
        # VWAP = Sum(Price * Volume) / Sum(Volume)
        typical_price = (data['high'] + data['low'] + data['close']) / 3.0
        price_volume = typical_price * data['volume']
        
        # Rolling window basado en número de velas
        # Para 4H: 1 día = 6 velas, 7 días = 42 velas
        if timeframe == '4h':
            window_size = period_days * 6
        elif timeframe == '1h':
            window_size = period_days * 24
        elif timeframe == '1d':
            window_size = period_days
        else:
            # Estimación conservadora
            window_size = period_days * 6
        
        # Calcular VWAP con rolling window
        rolling_pv = price_volume.rolling(window=window_size, min_periods=1).sum()
        rolling_vol = data['volume'].rolling(window=window_size, min_periods=1).sum()
        
        vwap = rolling_pv / rolling_vol
        vwap = vwap.ffill()  # Forward fill para reemplazar NaN
        
        return vwap
    
    def calculate_vwap_bands(
        self,
        data: pd.DataFrame,
        vwap: pd.Series,
        period_days: int,
        timeframe: str = '4h',
        num_std: float = 2.5
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calcula bandas VWAP usando desviaciones estándar.
        
        Args:
            data: DataFrame con 'close', 'high', 'low', 'volume'.
            vwap: Series con valores de VWAP.
            period_days: Días para el período de cálculo.
            timeframe: Timeframe de las velas.
            num_std: Número de desviaciones estándar para las bandas (default: 2.5).
            
        Returns:
            Tuple (upper_band, lower_band) con las bandas superior e inferior.
        """
        if len(vwap) != len(data):
            raise StrategyError("VWAP y datos deben tener la misma longitud")
        
        # Calcular desviación estándar de precios respecto a VWAP
        # Usar typical price (HLC/3) para el cálculo
        typical_price = (data['high'] + data['low'] + data['close']) / 3.0
        
        # Calcular desviación de precios respecto a VWAP
        price_deviation = typical_price - vwap
        
        # Calcular rolling window size (igual que VWAP)
        if timeframe == '4h':
            window_size = period_days * 6
        elif timeframe == '1h':
            window_size = period_days * 24
        elif timeframe == '1d':
            window_size = period_days
        else:
            window_size = period_days * 6
        
        # Calcular desviación estándar rolling
        std_dev = price_deviation.rolling(window=window_size, min_periods=1).std()
        std_dev = std_dev.ffill()
        
        # Calcular bandas
        upper_band = vwap + (std_dev * num_std)
        lower_band = vwap - (std_dev * num_std)
        
        return upper_band, lower_band
    
    def calculate_volume_profile(
        self,
        data: pd.DataFrame,
        period: int
    ) -> Dict[str, Any]:
        """
        Calcula Volume Profile de forma vectorizada.
        
        Retorna VPOC, VAH, VAL y LVN.
        
        Args:
            data: DataFrame con 'high', 'low', 'close', 'volume'.
            period: Número de velas para el período de análisis.
            
        Returns:
            Diccionario con:
            - vpoc: Precio con mayor volumen (float)
            - vah: Value Area High (float)
            - val: Value Area Low (float)
            - lvn_levels: Lista de precios LVN detectados (List[float])
            - volume_distribution: Series con distribución de volumen por precio
        """
        if len(data) < period:
            period = len(data)
        
        # Tomar últimos 'period' velas
        recent_data = data.tail(period).copy()
        
        # Crear bins de precio
        price_min = recent_data['low'].min()
        price_max = recent_data['high'].max()
        num_bins = 50  # Número de bins para el perfil
        
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Calcular volumen por bin (vectorizado)
        volume_by_bin = np.zeros(num_bins)
        
        for idx, row in recent_data.iterrows():
            high = row['high']
            low = row['low']
            volume = row['volume']
            
            # Distribuir volumen proporcionalmente entre bins que toca la vela
            touched_bins = np.where((bin_centers >= low) & (bin_centers <= high))[0]
            
            if len(touched_bins) > 0:
                # Distribuir volumen uniformemente entre bins tocados
                volume_per_bin = volume / len(touched_bins)
                volume_by_bin[touched_bins] += volume_per_bin
        
        # VPOC: Precio del bin con mayor volumen
        vpoc_idx = np.argmax(volume_by_bin)
        vpoc = bin_centers[vpoc_idx]
        
        # Value Area: 68% del volumen total
        total_volume = volume_by_bin.sum()
        target_volume = total_volume * self.value_area_percent
        
        # Ordenar bins por volumen descendente
        sorted_indices = np.argsort(volume_by_bin)[::-1]
        cumulative_volume = 0
        value_area_indices = []
        
        for idx in sorted_indices:
            cumulative_volume += volume_by_bin[idx]
            value_area_indices.append(idx)
            if cumulative_volume >= target_volume:
                break
        
        # VAH y VAL
        if value_area_indices:
            value_area_prices = bin_centers[value_area_indices]
            vah = value_area_prices.max()
            val = value_area_prices.min()
        else:
            vah = price_max
            val = price_min
        
        # Detectar LVN: Bins con volumen < 10% del promedio
        avg_volume = volume_by_bin.mean()
        lvn_threshold = avg_volume * 0.1
        lvn_indices = np.where(volume_by_bin < lvn_threshold)[0]
        lvn_levels = bin_centers[lvn_indices].tolist()
        
        # Crear distribución de volumen
        volume_distribution = pd.Series(volume_by_bin, index=bin_centers)
        
        return {
            'vpoc': vpoc,
            'vah': vah,
            'val': val,
            'lvn_levels': lvn_levels,
            'volume_distribution': volume_distribution
        }
    
    def calculate_cvd(self, data: pd.DataFrame) -> pd.Series:
        """
        Calcula Cumulative Volume Delta (CVD).
        
        CVD = Suma acumulada de (Buy Volume - Sell Volume)
        
        Args:
            data: DataFrame con 'close', 'high', 'low', 'volume'.
            
        Returns:
            Series con valores de CVD.
        """
        # Aproximación de Delta usando método de comparación de precios
        # Si close > open: más volumen de compra
        # Si close < open: más volumen de venta
        
        if 'open' not in data.columns:
            # Estimar open como close anterior
            data = data.copy()
            data['open'] = data['close'].shift(1).fillna(data['close'])
        
        # Calcular delta aproximado
        # Método: Si precio sube, asumir más volumen de compra
        price_change = data['close'] - data['open']
        price_range = data['high'] - data['low']
        
        # Evitar división por cero
        price_range = price_range.replace(0, 1)
        
        # Delta aproximado: proporción del volumen basada en movimiento de precio
        delta_ratio = price_change / price_range
        delta_ratio = delta_ratio.clip(-1, 1)  # Limitar entre -1 y 1
        
        # Delta = volumen * ratio
        delta = data['volume'] * delta_ratio
        
        # CVD = suma acumulada
        cvd = delta.cumsum()
        
        return cvd
    
    def calculate_adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calcula el Average Directional Index (ADX).
        
        Args:
            high: Series de precios máximos.
            low: Series de precios mínimos.
            close: Series de precios de cierre.
            period: Período para el cálculo (por defecto 14).
            
        Returns:
            Series con valores de ADX.
        """
        # Calcular True Range (TR)
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calcular Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        # Plus Directional Movement (+DM) y Minus Directional Movement (-DM)
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Suavizar TR, +DM y -DM con EMA
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Calcular DX (Directional Index)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        
        # ADX es la media móvil de DX
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx
    
    def detect_absorption_divergence(
        self,
        prices: pd.Series,
        cvd: pd.Series,
        lookback: int = 20
    ) -> Tuple[bool, bool, Optional[str]]:
        """
        Detecta divergencia de absorción entre precio y CVD.
        
        MEJORADO: Usa múltiples métodos de detección para ser más efectivo.
        
        Métodos de detección:
        1. Clásico: Lower Low en precio + Higher Low en CVD (y viceversa)
        2. Momentum divergente: Precio cae pero CVD sube (y viceversa)
        3. Desaceleración: Precio cae fuerte pero CVD cae poco (absorción parcial)
        
        Args:
            prices: Series de precios.
            cvd: Series de CVD.
            lookback: Período para buscar divergencias.
            
        Returns:
            Tuple (long_signal, short_signal, reason)
        """
        if len(prices) < lookback or len(cvd) < lookback:
            return False, False, None
        
        # Obtener últimos lookback valores
        recent_prices = prices.tail(lookback)
        recent_cvd = cvd.tail(lookback)
        
        long_signal = False
        short_signal = False
        reason = None
        
        # ============================================================
        # MÉTODO 1: Clásico - Lower Low / Higher Low (original mejorado)
        # ============================================================
        # Dividir el período en dos mitades para comparar
        half = lookback // 2
        first_half_prices = recent_prices.iloc[:half]
        second_half_prices = recent_prices.iloc[half:]
        first_half_cvd = recent_cvd.iloc[:half]
        second_half_cvd = recent_cvd.iloc[half:]
        
        # LONG: Precio hace nuevo mínimo pero CVD no
        price_min_1 = first_half_prices.min()
        price_min_2 = second_half_prices.min()
        cvd_min_1 = first_half_cvd.min()
        cvd_min_2 = second_half_cvd.min()
        
        # Divergencia alcista: precio más bajo pero CVD más alto
        if price_min_2 < price_min_1 and cvd_min_2 > cvd_min_1:
            long_signal = True
            reason = f"Absorción LONG (clásico): Precio LL ({price_min_2:.0f}<{price_min_1:.0f}), CVD HL"
        
        # SHORT: Precio hace nuevo máximo pero CVD no
        price_max_1 = first_half_prices.max()
        price_max_2 = second_half_prices.max()
        cvd_max_1 = first_half_cvd.max()
        cvd_max_2 = second_half_cvd.max()
        
        # Divergencia bajista: precio más alto pero CVD más bajo
        if price_max_2 > price_max_1 and cvd_max_2 < cvd_max_1:
            short_signal = True
            reason = f"Absorción SHORT (clásico): Precio HH ({price_max_2:.0f}>{price_max_1:.0f}), CVD LH"
        
        # ============================================================
        # MÉTODO 2: Momentum Divergente - Direcciones opuestas
        # ============================================================
        if not long_signal and not short_signal:
            # Calcular cambios porcentuales
            price_start = recent_prices.iloc[0]
            price_end = recent_prices.iloc[-1]
            price_change_pct = (price_end - price_start) / price_start * 100
            
            cvd_start = recent_cvd.iloc[0]
            cvd_end = recent_cvd.iloc[-1]
            cvd_change = cvd_end - cvd_start
            
            # Normalizar CVD change (usar std del período)
            cvd_std = recent_cvd.std()
            cvd_change_normalized = cvd_change / cvd_std if cvd_std > 0 else 0
            
            # LONG por absorción: Precio cae significativamente pero CVD sube
            # (Los vendedores venden pero hay compradores absorbiendo)
            if price_change_pct < -2.0 and cvd_change > 0:
                long_signal = True
                reason = f"Absorción LONG (momentum): Precio {price_change_pct:.1f}%, CVD subió"
            
            # SHORT por absorción: Precio sube significativamente pero CVD baja
            # (Los compradores compran pero hay vendedores absorbiendo)
            elif price_change_pct > 2.0 and cvd_change < 0:
                short_signal = True
                reason = f"Absorción SHORT (momentum): Precio +{price_change_pct:.1f}%, CVD bajó"
        
        # ============================================================
        # MÉTODO 3: Desaceleración - Absorción parcial
        # ============================================================
        if not long_signal and not short_signal:
            # Comparar la "velocidad" de caída del precio vs CVD
            price_start = recent_prices.iloc[0]
            price_end = recent_prices.iloc[-1]
            price_change_pct = (price_end - price_start) / price_start * 100
            
            # Calcular el cambio esperado de CVD basado en el histórico
            # Si normalmente cuando el precio cae X%, el CVD cae Y
            # Pero ahora el CVD cae mucho menos, hay absorción
            
            cvd_change = recent_cvd.iloc[-1] - recent_cvd.iloc[0]
            cvd_change_pct_of_range = cvd_change / (recent_cvd.max() - recent_cvd.min() + 1) * 100
            
            # LONG por desaceleración: Precio cae mucho pero CVD cae poco
            if price_change_pct < -3.0 and cvd_change_pct_of_range > -20:
                long_signal = True
                reason = f"Absorción LONG (desaceleración): Precio {price_change_pct:.1f}%, CVD resistió"
            
            # SHORT por desaceleración: Precio sube mucho pero CVD sube poco
            elif price_change_pct > 3.0 and cvd_change_pct_of_range < 20:
                short_signal = True
                reason = f"Absorción SHORT (desaceleración): Precio +{price_change_pct:.1f}%, CVD resistió"
        
        return long_signal, short_signal, reason
    
    def check_climatic_volatility(
        self,
        data: pd.DataFrame,
        current_idx: int
    ) -> bool:
        """
        Verifica si hay volatilidad climática (volumen > threshold * promedio).
        
        Args:
            data: DataFrame con 'volume'.
            current_idx: Índice de la vela actual.
            
        Returns:
            True si hay volatilidad climática (NO operar), False si es seguro operar.
        """
        if current_idx < self.min_volume_period:
            return False  # No hay suficientes datos
        
        # Calcular promedio y desviación estándar de volumen
        volume_window = data['volume'].iloc[current_idx - self.min_volume_period:current_idx]
        avg_volume = volume_window.mean()
        std_volume = volume_window.std()
        
        # Threshold: promedio + (threshold * std)
        threshold = avg_volume * self.volatility_threshold
        
        current_volume = data['volume'].iloc[current_idx]
        
        # Si volumen actual > threshold, hay volatilidad climática
        return current_volume > threshold
    
    def find_lvn_stop_loss(
        self,
        current_price: float,
        lvn_levels: list,
        direction: int  # 1 para long, -1 para short
    ) -> Optional[float]:
        """
        Encuentra el próximo LVN para colocar stop loss.
        
        Args:
            current_price: Precio actual.
            lvn_levels: Lista de niveles LVN.
            direction: 1 para long, -1 para short.
            
        Returns:
            Precio del stop loss basado en LVN, o None si no se encuentra.
        """
        if not lvn_levels:
            return None
        
        lvn_array = np.array(lvn_levels)
        
        if direction == 1:  # Long: stop loss debajo del precio
            # Encontrar LVN más cercano por debajo del precio
            below_lvn = lvn_array[lvn_array < current_price]
            if len(below_lvn) > 0:
                return float(below_lvn.max())  # El más alto por debajo
        else:  # Short: stop loss arriba del precio
            # Encontrar LVN más cercano por encima del precio
            above_lvn = lvn_array[lvn_array > current_price]
            if len(above_lvn) > 0:
                return float(above_lvn.min())  # El más bajo por encima
        
        return None
    
    def check_value_zone_retest(
        self,
        current_price: float,
        vpoc: float,
        vah: float,
        val: float,
        tolerance: float = 0.01  # 1% de tolerancia
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica si el precio está re-testando una zona de valor.
        
        Args:
            current_price: Precio actual.
            vpoc: VPOC del período anterior.
            vah: VAH del período anterior.
            val: VAL del período anterior.
            tolerance: Tolerancia porcentual para considerar "en zona".
            
        Returns:
            Tuple (is_retesting, zone_name)
        """
        # Verificar si está cerca de VPOC
        vpoc_tolerance = vpoc * tolerance
        if abs(current_price - vpoc) <= vpoc_tolerance:
            return True, "VPOC"
        
        # Verificar si está cerca de VAH
        vah_tolerance = vah * tolerance
        if abs(current_price - vah) <= vah_tolerance:
            return True, "VAH"
        
        # Verificar si está cerca de VAL
        val_tolerance = val * tolerance
        if abs(current_price - val) <= val_tolerance:
            return True, "VAL"
        
        # Verificar si está dentro de Value Area
        if val <= current_price <= vah:
            return True, "VALUE_AREA"
        
        return False, None
    
    def check_volume_confirmation(
        self,
        data: pd.DataFrame,
        i: int,
        direction: str  # 'LONG' o 'SHORT'
    ) -> bool:
        """
        Verifica que el volumen confirme la señal.
        
        Args:
            data: DataFrame con datos de mercado.
            i: Índice de la vela actual.
            direction: Dirección de la señal ('LONG' o 'SHORT').
            
        Returns:
            True si el volumen confirma la señal.
        """
        if not self.volume_confirmation_enabled:
            return True
        
        if 'open' not in data.columns or 'close' not in data.columns or 'volume' not in data.columns:
            return True  # Si no hay datos necesarios, permitir señal
        
        if i < 1:
            return True
        
        current_candle = data.iloc[i]
        current_volume = current_candle['volume']
        
        # Calcular volumen promedio reciente
        lookback = min(20, i)
        recent_volume_avg = data['volume'].iloc[i - lookback:i].mean() if lookback > 0 else current_volume
        
        # Determinar si la vela es alcista o bajista
        is_bullish = current_candle['close'] > current_candle['open']
        is_bearish = current_candle['close'] < current_candle['open']
        
        if direction == 'LONG':
            # Para LONG: necesitamos volumen alcista dominante
            # Verificar que volumen actual esté por encima del promedio
            volume_above_avg = current_volume >= recent_volume_avg * 1.2
            # Y que la vela sea alcista o al menos no muy bajista
            bullish_confirmation = is_bullish or (not is_bearish and current_candle['close'] >= current_candle['open'] * 0.998)
            return volume_above_avg and bullish_confirmation
        else:  # SHORT
            # Para SHORT: necesitamos volumen bajista dominante
            volume_above_avg = current_volume >= recent_volume_avg * 1.2
            bearish_confirmation = is_bearish or (not is_bullish and current_candle['close'] <= current_candle['open'] * 1.002)
            return volume_above_avg and bearish_confirmation
    
    def calculate_signal_strength(
        self,
        data: pd.DataFrame,
        i: int,
        direction: str,
        cvd_momentum: float,
        price: float,
        vwap: float,
        zone: str
    ) -> float:
        """
        Calcula un score de fuerza de la señal (0.0-1.0).
        
        Args:
            data: DataFrame con datos de mercado.
            i: Índice de la vela actual.
            direction: Dirección de la señal ('LONG' o 'SHORT').
            cvd_momentum: Momentum del CVD.
            price: Precio actual.
            vwap: VWAP actual.
            zone: Zona de valor (VPOC, VAH, VAL, VALUE_AREA).
            
        Returns:
            Score de fuerza entre 0.0 y 1.0.
        """
        score = 0.0
        
        # Componente 1: Magnitud del CVD momentum (0-0.3)
        # Normalizar CVD momentum (asumiendo valores típicos)
        abs_momentum = abs(cvd_momentum)
        # Normalizar a 0-1 basado en valores típicos (ajustar según mercado)
        momentum_normalized = min(abs_momentum / 50000.0, 1.0) if abs_momentum > 0 else 0.0
        score += momentum_normalized * 0.3
        
        # Componente 2: Distancia del precio a VWAP (0-0.2)
        # Precio cerca de VWAP es mejor para entrar
        if vwap > 0:
            price_distance_pct = abs(price - vwap) / vwap
            # Penalizar si está muy lejos de VWAP
            distance_score = max(0, 1.0 - (price_distance_pct * 10))  # Penalizar si >10% de distancia
            score += distance_score * 0.2
        
        # Componente 3: Zona de valor (0-0.2)
        zone_scores = {
            'VPOC': 0.8,
            'VAH': 0.6,
            'VAL': 0.6,
            'VALUE_AREA': 0.4
        }
        zone_score = zone_scores.get(zone, 0.2)
        score += zone_score * 0.2
        
        # Componente 4: Volumen relativo (0-0.3)
        if 'volume' in data.columns and i > 0:
            current_volume = data['volume'].iloc[i]
            lookback = min(20, i)
            avg_volume = data['volume'].iloc[i - lookback:i].mean() if lookback > 0 else current_volume
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume
                volume_score = min(volume_ratio / 2.0, 1.0)  # Normalizar a 0-1
                score += volume_score * 0.3
        
        return min(score, 1.0)  # Asegurar que no exceda 1.0
    
    def check_long_filters(
        self,
        data: pd.DataFrame,
        i: int,
        cvd: pd.Series,
        cvd_momentum: float,
        price: float,
        vwap: float
    ) -> Tuple[bool, str]:
        """
        Verifica filtros específicos adicionales para señales LONG.
        
        Args:
            data: DataFrame con datos de mercado.
            i: Índice de la vela actual.
            cvd: Series con valores de CVD.
            cvd_momentum: Momentum del CVD.
            price: Precio actual.
            vwap: VWAP actual.
            
        Returns:
            Tupla (es_valido, razon).
        """
        if not self.long_filters_enabled:
            return True, "Filtros LONG deshabilitados"
        
        # Filtro 1: Precio debe estar por encima de VWAP (ya verificado antes, pero reforzamos)
        if price <= vwap:
            return False, "Precio no está por encima de VWAP"
        
        # Filtro 2: CVD debe ser consistentemente positivo en últimos períodos
        if i >= 10:
            recent_cvd = cvd.iloc[i-10:i+1]
            if len(recent_cvd) > 0:
                cvd_positive_ratio = (recent_cvd > recent_cvd.iloc[0]).sum() / len(recent_cvd)
                if cvd_positive_ratio < 0.6:  # Al menos 60% de velas con CVD positivo
                    return False, f"CVD no consistentemente positivo ({cvd_positive_ratio*100:.0f}%)"
        
        # Filtro 3: Volumen de compra debe ser significativo
        if 'open' in data.columns and 'close' in data.columns and 'volume' in data.columns:
            if i > 0:
                lookback = min(20, i)
                avg_volume = data['volume'].iloc[i - lookback:i].mean() if lookback > 0 else data['volume'].iloc[i]
                current_volume = data['volume'].iloc[i]
                
                # Verificar que volumen alcista sea significativo
                is_bullish = data['close'].iloc[i] > data['open'].iloc[i]
                if is_bullish and avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    if volume_ratio < self.min_long_volume_ratio:
                        return False, f"Volumen insuficiente ({volume_ratio:.2f}x, mínimo {self.min_long_volume_ratio}x)"
        
        # Filtro 4: Momentum CVD debe ser positivo y significativo
        if cvd_momentum <= 0:
            return False, "CVD momentum no es positivo"
        
        return True, "Filtros LONG pasados"
    
    def check_short_filters(
        self,
        data: pd.DataFrame,
        i: int,
        cvd: pd.Series,
        cvd_momentum: float,
        price: float,
        vwap: float
    ) -> Tuple[bool, str]:
        """
        Verifica filtros específicos adicionales para señales SHORT.
        
        Args:
            data: DataFrame con datos de mercado.
            i: Índice de la vela actual.
            cvd: Series con valores de CVD.
            cvd_momentum: Momentum del CVD.
            price: Precio actual.
            vwap: VWAP actual.
            
        Returns:
            Tupla (es_valido, razon).
        """
        # Para SHORTs, filtros más simples por ahora
        # Precio debe estar por debajo de VWAP (ya verificado)
        if price >= vwap:
            return False, "Precio no está por debajo de VWAP"
        
        # CVD momentum debe ser negativo
        if cvd_momentum >= 0:
            return False, "CVD momentum no es negativo"
        
        return True, "Filtros SHORT pasados"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Genera señales basadas en Auction Market Theory.
        
        Args:
            data: DataFrame con 'open', 'high', 'low', 'close', 'volume'.
            
        Returns:
            Series con señales: 1 (compra), -1 (venta), 0 (mantener).
        """
        try:
            self.validate_data(data)
            
            # Validar columnas requeridas
            required_cols = ['high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                raise StrategyError(f"Faltan columnas requeridas: {missing_cols}")
            
            # Asegurar que hay suficientes datos
            min_periods = max(
                self.vwap_period_days * 6,  # VWAP para 4H
                self.volume_profile_period,
                self.delta_lookback,
                self.min_volume_period
            )
            
            if len(data) < min_periods:
                raise StrategyError(
                    f"Se requieren al menos {min_periods} períodos de datos, "
                    f"pero solo hay {len(data)}"
                )
            
            # Calcular indicadores
            # VWAP (detectar timeframe del índice de datos si es posible, o usar por defecto '4h')
            # Intentar detectar el timeframe del índice de datos
            detected_timeframe = '4h'  # Por defecto
            if isinstance(data.index, pd.DatetimeIndex) and len(data) > 1:
                time_diff = data.index[1] - data.index[0]
                if time_diff >= pd.Timedelta(hours=20) and time_diff <= pd.Timedelta(hours=28):
                    detected_timeframe = '1d'
                elif time_diff >= pd.Timedelta(hours=3) and time_diff <= pd.Timedelta(hours=5):
                    detected_timeframe = '4h'
            
            vwap = self.calculate_rolling_vwap(data, self.vwap_period_days, timeframe=detected_timeframe)
            
            # Volume Profile del período anterior
            vp_data = self.calculate_volume_profile(data, self.volume_profile_period)
            vpoc = vp_data['vpoc']
            vah = vp_data['vah']
            val = vp_data['val']
            lvn_levels = vp_data['lvn_levels']
            
            # CVD
            cvd = self.calculate_cvd(data)
            
            # ADX para filtro de regímenes de mercado (si está habilitado)
            adx = None
            if self.market_regime_enabled:
                adx = self.calculate_adx(data['high'], data['low'], data['close'], self.adx_period)
            
            # Inicializar señales
            signals = pd.Series(0, index=data.index, dtype=int)
            close_prices = data['close']
            
            # Variable para cooldown entre señales
            last_signal_index = -self.signal_cooldown - 1
            
            # Procesar cada vela
            for i in range(min_periods, len(signals)):
                current_price = close_prices.iloc[i]
                current_vwap = vwap.iloc[i]
                
                # 1. Filtro de tendencia
                trend_long = current_price > current_vwap
                trend_short = current_price < current_vwap
                
                if not (trend_long or trend_short):
                    continue  # Sin tendencia clara
                
                # 2. Filtro de volatilidad climática
                if self.check_climatic_volatility(data, i):
                    logger.debug(f"Vela {i}: Volatilidad climática detectada, saltando")
                    continue
                
                # 2.5. Filtro ADX de regímenes de mercado (si está habilitado)
                # Usar thresholds diferenciados para LONG vs SHORT
                if self.market_regime_enabled and adx is not None:
                    if i >= len(adx) or pd.isna(adx.iloc[i]):
                        continue  # No hay ADX disponible aún
                    # Determinar threshold según dirección de tendencia
                    adx_threshold_to_use = self.adx_threshold_long if trend_long else self.adx_threshold_short
                    if adx.iloc[i] < adx_threshold_to_use:
                        logger.debug(f"Vela {i}: ADX {adx.iloc[i]:.2f} < {adx_threshold_to_use}, mercado sin tendencia fuerte")
                        continue  # No hay tendencia fuerte, saltar señal
                
                # 3. Detectar divergencia de absorción PRIMERO (no requiere zona de valor)
                price_series = close_prices.iloc[:i+1]
                cvd_series = cvd.iloc[:i+1]
                
                long_div, short_div, reason = self.detect_absorption_divergence(
                    price_series,
                    cvd_series,
                    lookback=self.delta_lookback
                )
                
                # Identificar si es señal de ABSORCIÓN (divergencia real)
                is_absorption = (long_div or short_div) and reason and 'Absorción' in reason
                
                # 4. Verificar zona de valor (SOLO para señales de momentum, no absorción)
                is_retesting, zone = self.check_value_zone_retest(current_price, vpoc, vah, val)
                
                # Si no hay absorción Y no está en zona de valor, buscar momentum
                if not is_absorption and not is_retesting:
                    continue  # No hay absorción ni está en zona de valor
                
                # 5. Si no hay absorción, verificar momentum de CVD
                cvd_momentum = 0.0
                if not long_div and not short_div:
                    # Verificar momentum de CVD en la dirección de la tendencia
                    if i >= self.delta_lookback:
                        cvd_current = cvd_series.iloc[i]
                        cvd_prev = cvd_series.iloc[i - self.delta_lookback]
                        cvd_momentum = cvd_current - cvd_prev
                        
                        # Momentum positivo = compra, Momentum negativo = venta
                        if trend_long and cvd_momentum > 0:
                            # CVD subiendo en tendencia alcista = señal long
                            long_div = True
                            reason = f"CVD Momentum positivo: {cvd_momentum:.0f}"
                        elif trend_short and cvd_momentum < 0:
                            # CVD bajando en tendencia bajista = señal short
                            short_div = True
                            reason = f"CVD Momentum negativo: {cvd_momentum:.0f}"
                else:
                    # Si ya hay divergencia (absorción), calcular momentum para scoring
                    if i >= self.delta_lookback:
                        cvd_current = cvd_series.iloc[i]
                        cvd_prev = cvd_series.iloc[i - self.delta_lookback]
                        cvd_momentum = cvd_current - cvd_prev
                
                # 6. Generar señal
                # Cooldown entre señales (solo si está habilitado y es > 0)
                if self.signal_cooldown > 0 and i - last_signal_index < self.signal_cooldown:
                    logger.debug(f"Vela {i}: Cooldown activo (última señal en {last_signal_index})")
                    continue
                
                # Generar señal LONG
                # Para ABSORCIÓN: no requiere trend_long (precio > VWAP)
                # Para MOMENTUM: requiere trend_long
                if long_div:
                    # Verificar si LONGs están deshabilitados
                    if self.disable_longs:
                        logger.debug(f"Vela {i}: LONG bloqueada - LONGs deshabilitados")
                        continue
                    
                    # Para momentum, requiere trend_long; para absorción, no
                    if not is_absorption and not trend_long:
                        continue
                    
                    # Verificar filtro de tendencia mayor (si está habilitado y no es absorción)
                    if not is_absorption and self.require_uptrend_for_longs and i >= self.trend_filter_period:
                        sma_trend = close_prices.iloc[i - self.trend_filter_period:i].mean()
                        if current_price < sma_trend:
                            logger.debug(f"Vela {i}: LONG bloqueada - precio ({current_price:.2f}) < SMA{self.trend_filter_period} ({sma_trend:.2f})")
                            continue
                    
                    signals.iloc[i] = 1
                    last_signal_index = i
                    zone_str = zone if zone else 'EXTREMO'
                    logger.info(
                        f"Vela {i}: SEÑAL LONG. Razón: {reason}, "
                        f"Zona: {zone_str}, Precio: {current_price:.2f}, VWAP: {current_vwap:.2f}"
                    )
                
                # Generar señal SHORT
                # Para ABSORCIÓN: no requiere trend_short (precio < VWAP)
                # Para MOMENTUM: requiere trend_short
                elif short_div:
                    # Verificar si SHORTs están deshabilitados
                    if self.disable_shorts:
                        logger.debug(f"Vela {i}: SHORT bloqueada - SHORTs deshabilitados")
                        continue
                    
                    # Para momentum, requiere trend_short; para absorción, no
                    if not is_absorption and not trend_short:
                        continue
                    
                    signals.iloc[i] = -1
                    last_signal_index = i
                    zone_str = zone if zone else 'EXTREMO'
                    logger.info(
                        f"Vela {i}: SEÑAL SHORT. Razón: {reason}, "
                        f"Zona: {zone_str}, Precio: {current_price:.2f}, VWAP: {current_vwap:.2f}"
                    )
            
            total_signals = (signals != 0).sum()
            logger.info(f"VolumeValueStrategy: {total_signals} señales generadas")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generando señales: {e}", exc_info=True)
            raise StrategyError(f"Error generando señales: {e}") from e
    
    def get_params(self) -> Dict[str, Any]:
        """Retorna los parámetros de la estrategia."""
        return {
            'strategy_type': 'VOLUME_VALUE',
            'vwap_period_days': self.vwap_period_days,
            'volume_profile_period': self.volume_profile_period,
            'value_area_percent': self.value_area_percent,
            'delta_lookback': self.delta_lookback,
            'volatility_threshold': self.volatility_threshold,
            'min_volume_period': self.min_volume_period,
            'lvn_lookback': self.lvn_lookback,
            'market_regime_enabled': self.market_regime_enabled,
            'adx_period': self.adx_period,
            'adx_threshold': self.adx_threshold
        }
    
    def get_lvn_stop_loss(
        self,
        entry_price: float,
        direction: int,
        data: pd.DataFrame
    ) -> Optional[float]:
        """
        Método auxiliar para obtener stop loss basado en LVN.
        
        Args:
            entry_price: Precio de entrada.
            direction: 1 para long, -1 para short.
            data: DataFrame con datos históricos.
            
        Returns:
            Precio del stop loss o None.
        """
        vp_data = self.calculate_volume_profile(data, self.volume_profile_period)
        lvn_levels = vp_data['lvn_levels']
        
        return self.find_lvn_stop_loss(entry_price, lvn_levels, direction)
