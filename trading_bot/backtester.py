"""
Módulo Backtester: Simula ejecuciones de trading y calcula métricas de rendimiento.

Este módulo proporciona la clase Backtester para realizar backtesting
de estrategias sobre datos históricos y calcular métricas como retorno total,
Sharpe Ratio y Maximum Drawdown.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .exceptions import BacktesterError


logger = logging.getLogger(__name__)


class Backtester:
    """
    Clase para realizar backtesting de estrategias de trading.
    
    Simula las ejecuciones de trading basándose en señales de una estrategia
    y calcula diversas métricas de rendimiento.
    
    Attributes:
        initial_capital (float): Capital inicial para el backtest.
        commission (float): Comisión por operación (por defecto 0.001 = 0.1%).
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
        market_type: str = 'spot',
        leverage: float = 1.0,
        trailing_stop_activation: float = None,
        trailing_stop_distance: float = None,
        volume_reversal_period: int = None,
        volume_reversal_threshold: float = None,
        atr_period: int = None,
        atr_multiplier: float = None,
        tp_dynamic_enabled: bool = False,
        tp_partial_pct: float = None,
        tp_atr_multiplier: float = None,
        tp_vwap_band: float = None,
        strategy_instance: Any = None,  # VolumeValueStrategy instance para acceder a métodos
        exhaustion_exit_enabled: bool = False,  # Salida por divergencia de exhaustion
        exhaustion_lookback: int = 10,  # Período para detectar exhaustion
        # MEJORA DEL EXPERTO: Trailing Stop basado en ATR
        trailing_atr_enabled: bool = False,  # Usar ATR para trailing stop en lugar de porcentaje fijo
        trailing_atr_multiplier: float = 2.5,  # Multiplicador ATR para distancia del trailing stop
        # SMART TRAILING STOP (Híbrido Inteligente) - VERSIÓN CONSERVADORA
        smart_trailing_enabled: bool = False,  # Habilitar Smart Trailing Stop
        smart_trailing_atr_base: float = 1.5,  # Multiplicador ATR base (reducido de 2.0)
        smart_trailing_profit_phases: bool = True,  # Ajustar por fase de profit
        smart_trailing_time_decay: bool = True,  # Ajustar por tiempo en trade
        smart_trailing_breakeven_threshold: float = 0.02,  # Profit mínimo para breakeven (reducido de 3% a 2%)
        # SELECCIÓN AUTOMÁTICA DE TRAILING
        auto_trailing_selection: bool = False  # Selección automática: Smart para 15m/1h, Tradicional para 4h/1d
    ):
        """
        Inicializa el Backtester.
        
        Args:
            initial_capital: Capital inicial en USDT (por defecto 10000).
            commission: Comisión por operación como fracción (por defecto 0.001 = 0.1%).
            stop_loss_pct: Stop loss como porcentaje (ej: 0.05 = 5%, None para desactivar o usar ATR).
            take_profit_pct: Take profit como porcentaje (ej: 0.10 = 10%, None para desactivar).
            market_type: Tipo de mercado ('spot' o 'futures', por defecto 'spot').
            leverage: Apalancamiento (por defecto 1.0 = sin apalancamiento). Para spot debe ser 1.0.
            trailing_stop_activation: Ganancia mínima para activar trailing stop (ej: 0.05 = 5%, None para desactivar).
            trailing_stop_distance: Distancia del trailing stop desde el precio máximo (ej: 0.02 = 2%).
            volume_reversal_period: Período para validación de volumen en reversiones (None para desactivar).
            volume_reversal_threshold: Umbral de volumen para reversiones (None para desactivar).
            atr_period: Período para calcular ATR para stops dinámicos (None para usar stop_loss_pct).
            atr_multiplier: Multiplicador de ATR para calcular distancia de stop loss (None para usar stop_loss_pct).
            
        Raises:
            BacktesterError: Si los parámetros no son válidos.
        """
        if initial_capital <= 0:
            raise BacktesterError("El capital inicial debe ser mayor que 0")
        
        if commission < 0 or commission >= 1:
            raise BacktesterError("La comisión debe estar entre 0 y 1")
        
        if stop_loss_pct is not None and (stop_loss_pct <= 0 or stop_loss_pct >= 1):
            raise BacktesterError("El stop loss debe estar entre 0 y 1")
        
        if take_profit_pct is not None and (take_profit_pct <= 0 or take_profit_pct >= 1):
            raise BacktesterError("El take profit debe estar entre 0 y 1")
        
        market_type = market_type.lower()
        if market_type not in ['spot', 'futures']:
            raise BacktesterError("market_type debe ser 'spot' o 'futures'")
        
        if leverage < 1.0 or leverage > 125.0:
            raise BacktesterError("El leverage debe estar entre 1.0 y 125.0")
        
        if market_type == 'spot' and leverage != 1.0:
            raise BacktesterError("El mercado spot no soporta apalancamiento (leverage debe ser 1.0)")
        
        if atr_period is not None and atr_period < 1:
            raise BacktesterError("El período ATR debe ser mayor que 0")
        
        if atr_multiplier is not None and atr_multiplier <= 0:
            raise BacktesterError("El multiplicador ATR debe ser mayor que 0")
        
        if (atr_period is None) != (atr_multiplier is None):
            raise BacktesterError("atr_period y atr_multiplier deben estar ambos activados o ambos desactivados")
        
        # Permite usar ATR como stop dinámico principal y stop_loss_pct como hard stop de emergencia
        # Si ambos están presentes, se usa el más cercano (el más conservador)
        # ATR actúa como stop dinámico principal, stop_loss_pct como última línea de defensa
        
        self.initial_capital = initial_capital
        self.commission = commission
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.market_type = market_type
        self.leverage = leverage
        self.trailing_stop_activation = trailing_stop_activation
        self.trailing_stop_distance = trailing_stop_distance
        self.volume_reversal_period = volume_reversal_period
        self.volume_reversal_threshold = volume_reversal_threshold
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        
        # Scaling Out (Salidas Parciales)
        self.tp_dynamic_enabled = tp_dynamic_enabled
        self.tp_partial_pct = tp_partial_pct
        self.tp_atr_multiplier = tp_atr_multiplier
        self.tp_vwap_band = tp_vwap_band
        self.strategy_instance = strategy_instance  # Para calcular bandas VWAP si es necesario
        
        # Exhaustion Exit (Salida por divergencia CVD)
        self.exhaustion_exit_enabled = exhaustion_exit_enabled
        
        # Smart Trailing Stop (Híbrido Inteligente)
        self.smart_trailing_enabled = smart_trailing_enabled
        self.smart_trailing_atr_base = smart_trailing_atr_base
        self.smart_trailing_profit_phases = smart_trailing_profit_phases
        self.smart_trailing_time_decay = smart_trailing_time_decay
        self.smart_trailing_breakeven_threshold = smart_trailing_breakeven_threshold
        self.exhaustion_lookback = exhaustion_lookback
        
        # Selección Automática de Trailing
        self.auto_trailing_selection = auto_trailing_selection
        # Este valor se determinará en run_backtest basado en el timeframe detectado
        self._effective_smart_trailing = smart_trailing_enabled
        
        # MEJORA DEL EXPERTO: Trailing Stop basado en ATR
        self.trailing_atr_enabled = trailing_atr_enabled
        self.trailing_atr_multiplier = trailing_atr_multiplier
        
        # Hard stop de emergencia: activar automáticamente si no hay stop_loss_pct y hay leverage alto
        # Para evitar liquidaciones, usar un porcentaje seguro basado en leverage
        # Con 10x leverage, una caída de 10% = 100% pérdida (liquidación)
        # Hard stop de emergencia: 8% del precio (más estricto para prevenir liquidaciones)
        if stop_loss_pct is None and leverage > 1.0 and market_type == 'futures':
            # Calcular porcentaje seguro: 1/leverage * 0.8 (80% del límite de liquidación, más conservador)
            emergency_stop_pct = (1.0 / leverage) * 0.8
            # Limitar entre 5% y 8% para evitar stops demasiado cercanos o lejanos (más estricto)
            emergency_stop_pct = max(0.05, min(0.08, emergency_stop_pct))
            self.emergency_stop_pct = emergency_stop_pct
            logger.info(f"Hard stop de emergencia activado automáticamente: {emergency_stop_pct*100:.1f}% (para prevenir liquidaciones con {leverage}x leverage)")
        else:
            self.emergency_stop_pct = None
        
        sl_info = f", SL={stop_loss_pct*100:.1f}%" if stop_loss_pct else (f", SL=ATR({atr_period}x{atr_multiplier})" if atr_period else "")
        if self.emergency_stop_pct:
            sl_info += f"+Emerg({self.emergency_stop_pct*100:.1f}%)"
        tp_info = f", TP={take_profit_pct*100:.1f}%" if take_profit_pct else ""
        market_info = f", market={market_type}"
        lev_info = f", leverage={leverage}x" if leverage > 1.0 else ""
        logger.info(f"Backtester inicializado: capital={initial_capital}, commission={commission}{sl_info}{tp_info}{market_info}{lev_info}")
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """
        Calcula el ATR (Average True Range).
        
        Args:
            high: Series con los precios máximos.
            low: Series con los precios mínimos.
            close: Series con los precios de cierre.
            period: Período para el cálculo del ATR.
            
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
    
    def _detect_timeframe(self, data: pd.DataFrame) -> str:
        """
        Detecta el timeframe de los datos basándose en el índice.
        
        Args:
            data: DataFrame con índice DatetimeIndex.
            
        Returns:
            String con el timeframe detectado ('15m', '1h', '4h', '1d').
        """
        if not isinstance(data.index, pd.DatetimeIndex) or len(data) < 2:
            logger.warning("No se pudo detectar timeframe, usando '4h' por defecto")
            return '4h'
        
        # Calcular diferencia de tiempo entre las primeras velas
        time_diff = data.index[1] - data.index[0]
        
        # Clasificar por timeframe
        if time_diff <= pd.Timedelta(minutes=20):
            return '15m'
        elif time_diff <= pd.Timedelta(hours=1, minutes=30):
            return '1h'
        elif time_diff <= pd.Timedelta(hours=5):
            return '4h'
        else:
            return '1d'
    
    def _determine_trailing_type(self, timeframe: str) -> dict:
        """
        Determina el tipo de trailing óptimo basado en el timeframe.
        
        Basado en los resultados de backtesting:
        - 15m/1h: Smart Trailing (mejor rendimiento +30% más retorno)
        - 4h/1d: Tradicional (más estable, menor drawdown)
        
        Args:
            timeframe: String con el timeframe ('15m', '1h', '4h', '1d').
            
        Returns:
            Dict con la configuración de trailing.
        """
        if timeframe in ['15m', '1h']:
            # Smart Trailing - Mejor para timeframes cortos
            return {
                'use_smart': True,
                'atr_base': 1.5,  # Versión balanceada
                'profit_phases': True,
                'time_decay': True,
                'breakeven_threshold': 0.025,  # 2.5%
                'reason': f'Smart Trailing seleccionado para {timeframe} (mejor rendimiento en TF cortos)'
            }
        else:
            # Trailing Tradicional - Mejor para timeframes largos
            return {
                'use_smart': False,
                'reason': f'Trailing Tradicional seleccionado para {timeframe} (más estable en TF largos)'
            }
    
    def _calculate_cvd(self, data: pd.DataFrame) -> pd.Series:
        """
        Calcula el CVD (Cumulative Volume Delta).
        
        Usa el método del strategy_instance si está disponible,
        de lo contrario usa una aproximación basada en precio.
        
        Args:
            data: DataFrame con datos OHLCV.
            
        Returns:
            Series con los valores del CVD.
        """
        if self.strategy_instance is not None and hasattr(self.strategy_instance, 'calculate_cvd'):
            return self.strategy_instance.calculate_cvd(data)
        
        # Aproximación: delta = (close - open) / (high - low) * volume
        if all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            range_hl = data['high'] - data['low']
            range_hl = range_hl.replace(0, 0.0001)  # Evitar división por cero
            delta = ((data['close'] - data['open']) / range_hl) * data['volume']
            return delta.cumsum()
        
        return pd.Series(0, index=data.index)
    
    def _calculate_smart_trailing_stop(
        self,
        position_type: str,  # 'LONG' o 'SHORT'
        entry_price: float,
        current_price: float,
        extreme_price: float,  # highest_price para LONG, lowest_price para SHORT
        atr_value: float,
        bars_in_trade: int,
        cvd_exhaustion: bool = False
    ) -> float:
        """
        Calcula el Smart Trailing Stop (Híbrido Inteligente).
        
        Combina múltiples factores para determinar la distancia óptima del trailing stop:
        1. ATR dinámico como base
        2. Ajuste por fase de profit (más holgado al inicio, más ajustado con ganancias)
        3. Ajuste por tiempo en trade (trades largos se ajustan más)
        4. Ajuste por exhaustion (si se detecta, ajustar agresivamente)
        5. Protección de breakeven después de cierto profit
        
        Args:
            position_type: 'LONG' o 'SHORT'
            entry_price: Precio de entrada de la posición
            current_price: Precio actual
            extreme_price: Máximo alcanzado (LONG) o mínimo alcanzado (SHORT)
            atr_value: Valor actual del ATR
            bars_in_trade: Número de velas desde la entrada
            cvd_exhaustion: Si se detectó divergencia de exhaustion
            
        Returns:
            Precio del trailing stop
        """
        # Calcular profit actual
        if position_type == 'LONG':
            current_profit_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            current_profit_pct = (entry_price - current_price) / entry_price
        
        # Base: ATR dinámico
        base_distance = atr_value * self.smart_trailing_atr_base
        
        # Factor de ajuste inicial
        distance_multiplier = 1.0
        
        # 1. Ajuste por FASE DE PROFIT (BALANCEADO - proteger ganancias sin cerrar muy pronto)
        if self.smart_trailing_profit_phases:
            if current_profit_pct < 0.01:
                # Fase muy inicial (0-1%): dar espacio pero no demasiado
                distance_multiplier = 1.4
            elif current_profit_pct < 0.02:
                # Fase inicial (1-2%): espacio moderado
                distance_multiplier = 1.2
            elif current_profit_pct < 0.04:
                # Profit bajo (2-4%): normal
                distance_multiplier = 1.0
            elif current_profit_pct < 0.06:
                # Profit medio (4-6%): empezar a proteger
                distance_multiplier = 0.8
            elif current_profit_pct < 0.10:
                # Profit alto (6-10%): proteger
                distance_multiplier = 0.6
            else:
                # Profit muy alto (>10%): proteger agresivamente
                distance_multiplier = 0.4
        
        # 2. Ajuste por TIEMPO EN TRADE (BALANCEADO - decay progresivo)
        if self.smart_trailing_time_decay:
            if bars_in_trade > 60:
                # Trade muy largo: ajustar agresivamente
                distance_multiplier *= 0.55
            elif bars_in_trade > 40:
                # Trade largo: ajustar moderadamente
                distance_multiplier *= 0.7
            elif bars_in_trade > 20:
                # Trade medio: ajuste leve
                distance_multiplier *= 0.85
            # Trade corto (<20 bars): sin ajuste adicional
        
        # 3. Ajuste por EXHAUSTION (divergencia CVD)
        if cvd_exhaustion:
            # Si hay señal de exhaustion, ajustar MUY agresivamente
            distance_multiplier *= 0.4
            logger.debug(f"Smart Trailing: Exhaustion detectado, multiplicador reducido a {distance_multiplier:.2f}")
        
        # Calcular distancia final
        final_distance = base_distance * distance_multiplier
        
        # Calcular precio del stop
        if position_type == 'LONG':
            stop_price = extreme_price - final_distance
            
            # 4. Protección de BREAKEVEN
            if current_profit_pct >= self.smart_trailing_breakeven_threshold:
                # Mínimo: breakeven + 0.5%
                min_stop = entry_price * 1.005
                stop_price = max(stop_price, min_stop)
                
        else:  # SHORT
            stop_price = extreme_price + final_distance
            
            # Protección de breakeven para SHORT
            if current_profit_pct >= self.smart_trailing_breakeven_threshold:
                # Máximo: breakeven - 0.5%
                max_stop = entry_price * 0.995
                stop_price = min(stop_price, max_stop)
        
        logger.debug(
            f"Smart Trailing [{position_type}]: profit={current_profit_pct*100:.1f}%, "
            f"bars={bars_in_trade}, base_dist={base_distance:.2f}, "
            f"mult={distance_multiplier:.2f}, final_dist={final_distance:.2f}, "
            f"stop={stop_price:.2f}"
        )
        
        return stop_price
    
    def _detect_exhaustion_divergence(
        self,
        prices: pd.Series,
        cvd: pd.Series,
        position_type: str,
        lookback: int = 10,
        min_profit_pct: float = 0.01
    ) -> Tuple[bool, Optional[str]]:
        """
        Detecta divergencia de exhaustion para cerrar posiciones.
        
        LONG: Precio Higher High + CVD Lower High = Cerrar (compradores agotados)
        SHORT: Precio Lower Low + CVD Higher Low = Cerrar (vendedores agotados)
        
        Solo se activa si la posición está en ganancia.
        
        Args:
            prices: Series de precios de cierre.
            cvd: Series de CVD.
            position_type: 'LONG' o 'SHORT'.
            lookback: Período para buscar divergencia.
            min_profit_pct: Ganancia mínima para considerar cerrar (por defecto 1%).
            
        Returns:
            Tuple (exhaustion_detected, reason)
        """
        if len(prices) < lookback or len(cvd) < lookback:
            return False, None
        
        recent_prices = prices.tail(lookback)
        recent_cvd = cvd.tail(lookback)
        
        # Dividir en dos mitades para comparar extremos
        half = lookback // 2
        first_half_prices = recent_prices.iloc[:half]
        second_half_prices = recent_prices.iloc[half:]
        first_half_cvd = recent_cvd.iloc[:half]
        second_half_cvd = recent_cvd.iloc[half:]
        
        if position_type == 'LONG':
            # Buscar: Precio Higher High + CVD Lower High (agotamiento de compradores)
            price_max_1 = first_half_prices.max()
            price_max_2 = second_half_prices.max()
            cvd_max_1 = first_half_cvd.max()
            cvd_max_2 = second_half_cvd.max()
            
            # Requerir que el precio haga un nuevo máximo
            if price_max_2 > price_max_1:
                # Requerir que el CVD NO haga un nuevo máximo (divergencia)
                if cvd_max_2 < cvd_max_1:
                    # Calcular la magnitud de la divergencia (para filtrar ruido)
                    price_diff_pct = (price_max_2 - price_max_1) / price_max_1 * 100
                    cvd_diff = cvd_max_1 - cvd_max_2
                    
                    # Solo reportar si la divergencia es significativa
                    if price_diff_pct > 0.5:  # Al menos 0.5% de nuevo máximo
                        return True, f"Exhaustion LONG: Precio HH (+{price_diff_pct:.1f}%), CVD LH (compradores agotados)"
        
        elif position_type == 'SHORT':
            # Buscar: Precio Lower Low + CVD Higher Low (agotamiento de vendedores)
            price_min_1 = first_half_prices.min()
            price_min_2 = second_half_prices.min()
            cvd_min_1 = first_half_cvd.min()
            cvd_min_2 = second_half_cvd.min()
            
            # Requerir que el precio haga un nuevo mínimo
            if price_min_2 < price_min_1:
                # Requerir que el CVD NO haga un nuevo mínimo (divergencia)
                if cvd_min_2 > cvd_min_1:
                    # Calcular la magnitud de la divergencia
                    price_diff_pct = (price_min_1 - price_min_2) / price_min_1 * 100
                    
                    # Solo reportar si la divergencia es significativa
                    if price_diff_pct > 0.5:  # Al menos 0.5% de nuevo mínimo
                        return True, f"Exhaustion SHORT: Precio LL (-{price_diff_pct:.1f}%), CVD HL (vendedores agotados)"
        
        return False, None
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        signals: pd.Series
    ) -> pd.DataFrame:
        """
        Ejecuta el backtest sobre los datos históricos.
        
        Args:
            data: DataFrame con datos históricos (debe incluir 'close').
            signals: Series con señales de trading (1=compra, -1=venta, 0=mantener).
            
        Returns:
            DataFrame con el histórico de posiciones y capital.
            
        Raises:
            BacktesterError: Si hay error al ejecutar el backtest.
        """
        try:
            if data.empty:
                raise BacktesterError("El DataFrame de datos está vacío")
            
            if signals.empty:
                raise BacktesterError("La serie de señales está vacía")
            
            if len(data) != len(signals):
                raise BacktesterError("Los datos y las señales deben tener la misma longitud")
            
            if not data.index.equals(signals.index):
                raise BacktesterError("Los índices de datos y señales deben coincidir")
            
            logger.info(f"Iniciando backtest sobre {len(data)} períodos")
            
            # SELECCIÓN AUTOMÁTICA DE TRAILING
            if self.auto_trailing_selection:
                detected_tf = self._detect_timeframe(data)
                trailing_config = self._determine_trailing_type(detected_tf)
                logger.info(f"📊 Auto-Trailing: {trailing_config['reason']}")
                
                if trailing_config['use_smart']:
                    # Activar Smart Trailing con configuración óptima
                    self._effective_smart_trailing = True
                    self.smart_trailing_atr_base = trailing_config['atr_base']
                    self.smart_trailing_profit_phases = trailing_config['profit_phases']
                    self.smart_trailing_time_decay = trailing_config['time_decay']
                    self.smart_trailing_breakeven_threshold = trailing_config['breakeven_threshold']
                else:
                    # Usar trailing tradicional
                    self._effective_smart_trailing = False
            else:
                # Usar la configuración manual
                self._effective_smart_trailing = self.smart_trailing_enabled
            
            # Inicializar variables
            capital = self.initial_capital
            available_capital = self.initial_capital  # Capital disponible para nuevas posiciones
            # position: 0 = sin posición, >0 = largo, <0 = corto (solo futures)
            position = 0.0
            entry_price = 0.0
            entry_capital = 0.0  # Capital usado como margen en la posición actual
            stop_loss_price = 0.0
            take_profit_price = 0.0
            # Variables para trailing stop
            trailing_stop_active = False
            highest_price = 0.0  # Precio más alto alcanzado (para largos)
            lowest_price = float('inf')  # Precio más bajo alcanzado (para cortos)
            trailing_stop_price = 0.0  # Precio del trailing stop
            
            # Variables para Scaling Out (Salidas Parciales)
            tp_partial_executed = False  # Si ya se ejecutó TP parcial
            original_position_size = 0.0  # Tamaño original de la posición
            original_entry_capital = 0.0  # Capital original de entrada
            tp1_price = 0.0  # Precio objetivo para TP1 (dinámico)
            vwap_upper_band = None  # Banda superior VWAP (si se usa)
            vwap_lower_band = None  # Banda inferior VWAP (si se usa)
            
            # Lista para rastrear eventos de liquidación
            liquidation_events = []
            
            # Diccionario para rastrear exit_reason de cada operación
            # Key: índice donde se cierra la posición, Value: exit_reason
            trade_exit_reasons = {}
            
            # Diccionario para rastrear ganancias de TPs parciales por posición
            # Key: índice de entrada de la posición, Value: ganancia del TP parcial
            tp_partial_profits = {}
            
            # Variable para rastrear el índice de entrada de la posición actual
            current_entry_index = None
            current_position_type = None  # 'LONG' o 'SHORT'
            
            # Crear DataFrame de resultados
            results = pd.DataFrame(index=data.index)
            results['close'] = data['close']
            results['signal'] = signals
            results['position'] = 0.0  # Float para permitir valores decimales
            results['capital'] = float(self.initial_capital)
            results['returns'] = 0.0
            results['cumulative_returns'] = 0.0
            
            # Obtener high y low para validación de stop loss con gaps
            high_prices = data['high'] if 'high' in data.columns else data['close']
            low_prices = data['low'] if 'low' in data.columns else data['close']
            close_prices = data['close']
            volume_data = data['volume'] if 'volume' in data.columns else None
            
            # Calcular ATR si está habilitado para stops dinámicos
            atr_values = None
            if self.atr_period is not None and self.atr_multiplier is not None:
                if all(col in data.columns for col in ['high', 'low', 'close']):
                    atr_values = self._calculate_atr(high_prices, low_prices, close_prices, self.atr_period)
                else:
                    logger.warning("Columnas 'high', 'low', 'close' requeridas para ATR, usando stop_loss_pct en su lugar")
                    # Si no hay ATR, debería haber stop_loss_pct
                    if self.stop_loss_pct is None:
                        raise BacktesterError("ATR requiere columnas high/low/close, pero stop_loss_pct no está definido")
            
            # Calcular CVD si está habilitada la salida por exhaustion
            cvd_values = None
            if self.exhaustion_exit_enabled:
                cvd_values = self._calculate_cvd(data)
                logger.info(f"Exhaustion Exit habilitado: lookback={self.exhaustion_lookback} velas")
            
            # Calcular bandas VWAP si se usan para TP dinámico
            if self.tp_dynamic_enabled and self.tp_vwap_band is not None and self.strategy_instance is not None:
                try:
                    # Detectar timeframe del índice
                    detected_timeframe = '4h'
                    if isinstance(data.index, pd.DatetimeIndex) and len(data) > 1:
                        time_diff = data.index[1] - data.index[0]
                        if time_diff >= pd.Timedelta(hours=20) and time_diff <= pd.Timedelta(hours=28):
                            detected_timeframe = '1d'
                        elif time_diff >= pd.Timedelta(hours=3) and time_diff <= pd.Timedelta(hours=5):
                            detected_timeframe = '4h'
                    
                    vwap = self.strategy_instance.calculate_rolling_vwap(
                        data, 
                        self.strategy_instance.vwap_period_days,
                        timeframe=detected_timeframe
                    )
                    vwap_upper_band, vwap_lower_band = self.strategy_instance.calculate_vwap_bands(
                        data,
                        vwap,
                        self.strategy_instance.vwap_period_days,
                        timeframe=detected_timeframe,
                        num_std=self.tp_vwap_band
                    )
                    logger.info(f"Bandas VWAP calculadas para TP dinámico: {self.tp_vwap_band} desviaciones estándar")
                except Exception as e:
                    logger.warning(f"Error calculando bandas VWAP: {e}, usando solo ATR para TP dinámico")
                    vwap_upper_band = None
                    vwap_lower_band = None
            
            # Simular trading
            for i in range(len(results)):
                price = results['close'].iloc[i]
                high = high_prices.iloc[i]
                low = low_prices.iloc[i]
                signal = results['signal'].iloc[i]
                
                # Verificar stop loss y take profit si hay posición (usando high/low para manejar gaps)
                if position != 0 and entry_price > 0:
                    # Posición LARGA (position > 0)
                    if position > 0:
                        # Actualizar precio máximo para trailing stop
                        if high > highest_price:
                            highest_price = high
                        
                        # Calcular ganancia actual
                        current_profit_pct = (price - entry_price) / entry_price
                        
                        # Activar trailing stop si se alcanza el umbral de activación
                        if (self.trailing_stop_activation is not None and 
                            not trailing_stop_active and 
                            current_profit_pct >= self.trailing_stop_activation):
                            trailing_stop_active = True
                            
                            # SMART TRAILING STOP (Híbrido Inteligente)
                            if self._effective_smart_trailing and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                # Calcular barras en trade
                                bars_in_trade = i - current_entry_index if current_entry_index is not None else 0
                                
                                # Detectar exhaustion si está habilitado
                                cvd_exhaustion = False
                                if self.exhaustion_exit_enabled and cvd is not None:
                                    cvd_exhaustion, _ = self._detect_exhaustion_divergence(
                                        close_prices.iloc[:i+1], cvd.iloc[:i+1], 'LONG', self.exhaustion_lookback
                                    )
                                
                                trailing_stop_price = self._calculate_smart_trailing_stop(
                                    position_type='LONG',
                                    entry_price=entry_price,
                                    current_price=price,
                                    extreme_price=highest_price,
                                    atr_value=atr_values.iloc[i],
                                    bars_in_trade=bars_in_trade,
                                    cvd_exhaustion=cvd_exhaustion
                                )
                                logger.debug(f"Smart Trailing LARGO activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}")
                            
                            # Trailing Stop basado en ATR (sin smart)
                            elif self.trailing_atr_enabled and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                trailing_distance = atr_values.iloc[i] * self.trailing_atr_multiplier
                                trailing_stop_price = highest_price - trailing_distance
                                logger.debug(f"Trailing stop LARGO (ATR) activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}, ATR_dist={trailing_distance:.2f}")
                            else:
                                trailing_stop_price = highest_price * (1 - self.trailing_stop_distance)
                                logger.debug(f"Trailing stop LARGO activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}")
                        
                        # Actualizar trailing stop si está activo
                        if trailing_stop_active and (self.trailing_stop_distance is not None or self.trailing_atr_enabled or self._effective_smart_trailing):
                            # SMART TRAILING STOP (Híbrido Inteligente) - Actualización
                            if self._effective_smart_trailing and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                bars_in_trade = i - current_entry_index if current_entry_index is not None else 0
                                
                                cvd_exhaustion = False
                                if self.exhaustion_exit_enabled and cvd is not None:
                                    cvd_exhaustion, _ = self._detect_exhaustion_divergence(
                                        close_prices.iloc[:i+1], cvd.iloc[:i+1], 'LONG', self.exhaustion_lookback
                                    )
                                
                                new_trailing_stop = self._calculate_smart_trailing_stop(
                                    position_type='LONG',
                                    entry_price=entry_price,
                                    current_price=price,
                                    extreme_price=highest_price,
                                    atr_value=atr_values.iloc[i],
                                    bars_in_trade=bars_in_trade,
                                    cvd_exhaustion=cvd_exhaustion
                                )
                            # Trailing ATR (sin smart)
                            elif self.trailing_atr_enabled and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                trailing_distance = atr_values.iloc[i] * self.trailing_atr_multiplier
                                new_trailing_stop = highest_price - trailing_distance
                            else:
                                new_trailing_stop = highest_price * (1 - self.trailing_stop_distance)
                            
                            if new_trailing_stop > trailing_stop_price:
                                trailing_stop_price = new_trailing_stop
                                logger.debug(f"Trailing stop LARGO actualizado en {results.index[i]}: nuevo={trailing_stop_price:.2f}")
                        
                        # ORDEN CORRECTO: Verificar stops ANTES de liquidación
                        # Esto permite que los stops actúen como deben antes de que se detecte liquidación
                        
                        # 0. Verificar TP Parcial (Scaling Out) si está habilitado y no se ha ejecutado
                        # Primero, recalcular TP1 dinámico en cada vela (puede cambiar con volatilidad)
                        if self.tp_dynamic_enabled and not tp_partial_executed and tp1_price > 0:
                            # Recalcular TP1 dinámico usando valores actuales
                            tp1_candidates = []
                            
                            # TP1 basado en ATR (actualizado)
                            if self.tp_atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    tp1_atr = entry_price + (atr_value * self.tp_atr_multiplier)
                                    tp1_candidates.append(tp1_atr)
                            
                            # TP1 basado en VWAP upper band (actualizado)
                            if vwap_upper_band is not None:
                                if not pd.isna(vwap_upper_band.iloc[i]):
                                    tp1_vwap = vwap_upper_band.iloc[i]
                                    tp1_candidates.append(tp1_vwap)
                            
                            # Usar el más cercano (más conservador) si hay múltiples candidatos
                            if tp1_candidates:
                                tp1_price = min(tp1_candidates)
                        
                        # Verificar si TP Parcial debe ejecutarse (solo si estamos en ganancia)
                        if (self.tp_dynamic_enabled and not tp_partial_executed and 
                            tp1_price > 0 and tp1_price > entry_price and high >= tp1_price):
                            # Ejecutar cierre parcial
                            partial_position_size = original_position_size * self.tp_partial_pct
                            partial_entry_capital = original_entry_capital * self.tp_partial_pct
                            execution_price = tp1_price
                            
                            # Calcular P&L de la parte parcial
                            partial_pnl = partial_position_size * (execution_price - entry_price) * (1 - self.commission)
                            
                            # SOLO ejecutar si hay ganancia real
                            if partial_pnl > 0:
                                # Reducir posición y capital de la parte que sigue en el mercado
                                position = position - partial_position_size
                                entry_capital = entry_capital - partial_entry_capital
                                
                                # El capital disponible ahora incluye:
                                # 1. Lo que se obtuvo del cierre parcial (entry_capital parcial + pnl)
                                # 2. NOTA: el resto del capital sigue "invertido" en la posición abierta
                                available_capital = partial_entry_capital + partial_pnl
                                
                                # El capital total es el disponible más el valor de la posición restante
                                # La posición restante tiene valor: entry_capital (ya reducido)
                                capital = available_capital + entry_capital
                                
                                # Registrar ganancia del TP parcial para cálculo correcto en get_trades()
                                if current_entry_index is not None:
                                    tp_partial_profits[current_entry_index] = tp_partial_profits.get(current_entry_index, 0) + partial_pnl
                                
                                # Marcar como ejecutado
                                tp_partial_executed = True
                                
                                # Mover stop loss a breakeven (precio de entrada)
                                stop_loss_price = entry_price
                                
                                logger.info(
                                    f"TP Parcial LARGO alcanzado en {results.index[i]}: "
                                    f"Asegurando {self.tp_partial_pct*100:.0f}% de ganancias ({partial_pnl:.2f} USDT), "
                                    f"Stop Loss movido a Breakeven ({entry_price:.2f})"
                                )
                        
                        # 0.5. Verificar EXHAUSTION (verificación independiente, no bloquea otros stops)
                        position_closed_by_exhaustion = False
                        if self.exhaustion_exit_enabled and cvd_values is not None and i >= self.exhaustion_lookback:
                            current_profit_pct_ex = (price - entry_price) / entry_price
                            # Solo considerar si estamos en ganancia (al menos 2%)
                            if current_profit_pct_ex >= 0.02:
                                exhaustion, reason = self._detect_exhaustion_divergence(
                                    close_prices.iloc[:i+1],
                                    cvd_values.iloc[:i+1],
                                    'LONG',
                                    lookback=self.exhaustion_lookback
                                )
                                if exhaustion:
                                    # Cerrar posición por exhaustion
                                    execution_price = price
                                    pnl = position * (execution_price - entry_price) * (1 - self.commission)
                                    available_capital = entry_capital + pnl
                                    capital = available_capital
                                    if current_entry_index is not None:
                                        trade_exit_reasons[i] = 'EXHAUSTION'
                                    position = 0.0
                                    entry_price = 0.0
                                    entry_capital = 0.0
                                    stop_loss_price = 0.0
                                    take_profit_price = 0.0
                                    trailing_stop_active = False
                                    highest_price = 0.0
                                    trailing_stop_price = 0.0
                                    tp_partial_executed = False
                                    original_position_size = 0.0
                                    original_entry_capital = 0.0
                                    tp1_price = 0.0
                                    current_entry_index = None
                                    current_position_type = None
                                    position_closed_by_exhaustion = True
                                    logger.info(f"EXHAUSTION LONG en {results.index[i]}: {reason}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # 1. Verificar trailing stop primero (tiene máxima prioridad) - solo si no se cerró por exhaustion
                        if not position_closed_by_exhaustion and trailing_stop_active and low <= trailing_stop_price:
                            execution_price = trailing_stop_price
                            pnl = position * (execution_price - entry_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            highest_price = 0.0
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            logger.debug(f"Trailing Stop LARGO activado en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}")
                        
                        # 2. Verificar stop loss ANTES de liquidación (usando low para detectar si se tocó en la vela)
                        elif not position_closed_by_exhaustion and stop_loss_price > 0 and low <= stop_loss_price:
                            # Stop loss largo activado (precio bajó hasta el stop loss o más)
                            # Usar el precio del stop loss como precio de ejecución (no el low)
                            execution_price = stop_loss_price
                            # Con leverage: recuperamos el capital inicial + P&L
                            pnl = position * (execution_price - entry_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            # Rastrear exit_reason antes de resetear variables
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'STOP_LOSS'
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            highest_price = 0.0
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            current_entry_index = None
                            current_position_type = None
                            logger.info(f"Cierre LARGO: Stop Loss en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # Verificar take profit (usando high para detectar si se tocó en la vela)
                        elif not position_closed_by_exhaustion and self.take_profit_pct is not None and high >= take_profit_price:
                            # Take profit largo activado (precio subió hasta el take profit o más)
                            # Usar el precio del take profit como precio de ejecución
                            execution_price = take_profit_price
                            pnl = position * (execution_price - entry_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            # Rastrear exit_reason antes de resetear variables
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'TAKE_PROFIT'
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            highest_price = 0.0
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            current_entry_index = None
                            current_position_type = None
                            logger.info(f"Cierre LARGO: Take Profit en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                    
                    # Posición CORTA (position < 0, solo en futures)
                    elif position < 0 and self.market_type == 'futures':
                        # En corto: ganamos cuando baja, perdemos cuando sube
                        position_size = abs(position)
                        
                        # Actualizar precio mínimo para trailing stop
                        if low < lowest_price:
                            lowest_price = low
                        
                        # Calcular ganancia actual (en corto, ganamos cuando baja)
                        current_profit_pct = (entry_price - price) / entry_price
                        
                        # Activar trailing stop si se alcanza el umbral de activación
                        if (self.trailing_stop_activation is not None and 
                            not trailing_stop_active and 
                            current_profit_pct >= self.trailing_stop_activation):
                            trailing_stop_active = True
                            
                            # SMART TRAILING STOP (Híbrido Inteligente)
                            if self._effective_smart_trailing and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                bars_in_trade = i - current_entry_index if current_entry_index is not None else 0
                                
                                cvd_exhaustion = False
                                if self.exhaustion_exit_enabled and cvd is not None:
                                    cvd_exhaustion, _ = self._detect_exhaustion_divergence(
                                        close_prices.iloc[:i+1], cvd.iloc[:i+1], 'SHORT', self.exhaustion_lookback
                                    )
                                
                                trailing_stop_price = self._calculate_smart_trailing_stop(
                                    position_type='SHORT',
                                    entry_price=entry_price,
                                    current_price=price,
                                    extreme_price=lowest_price,
                                    atr_value=atr_values.iloc[i],
                                    bars_in_trade=bars_in_trade,
                                    cvd_exhaustion=cvd_exhaustion
                                )
                                logger.debug(f"Smart Trailing CORTO activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}")
                            
                            # Trailing Stop basado en ATR (sin smart)
                            elif self.trailing_atr_enabled and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                trailing_distance = atr_values.iloc[i] * self.trailing_atr_multiplier
                                trailing_stop_price = lowest_price + trailing_distance
                                logger.debug(f"Trailing stop CORTO (ATR) activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}, ATR_dist={trailing_distance:.2f}")
                            else:
                                trailing_stop_price = lowest_price * (1 + self.trailing_stop_distance)
                                logger.debug(f"Trailing stop CORTO activado en {results.index[i]}: precio={price:.2f}, trailing_stop={trailing_stop_price:.2f}")
                        
                        # Actualizar trailing stop si está activo
                        if trailing_stop_active and (self.trailing_stop_distance is not None or self.trailing_atr_enabled or self._effective_smart_trailing):
                            # SMART TRAILING STOP (Híbrido Inteligente) - Actualización
                            if self._effective_smart_trailing and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                bars_in_trade = i - current_entry_index if current_entry_index is not None else 0
                                
                                cvd_exhaustion = False
                                if self.exhaustion_exit_enabled and cvd is not None:
                                    cvd_exhaustion, _ = self._detect_exhaustion_divergence(
                                        close_prices.iloc[:i+1], cvd.iloc[:i+1], 'SHORT', self.exhaustion_lookback
                                    )
                                
                                new_trailing_stop = self._calculate_smart_trailing_stop(
                                    position_type='SHORT',
                                    entry_price=entry_price,
                                    current_price=price,
                                    extreme_price=lowest_price,
                                    atr_value=atr_values.iloc[i],
                                    bars_in_trade=bars_in_trade,
                                    cvd_exhaustion=cvd_exhaustion
                                )
                            # Trailing ATR (sin smart)
                            elif self.trailing_atr_enabled and atr_values is not None and not pd.isna(atr_values.iloc[i]):
                                trailing_distance = atr_values.iloc[i] * self.trailing_atr_multiplier
                                new_trailing_stop = lowest_price + trailing_distance
                            else:
                                new_trailing_stop = lowest_price * (1 + self.trailing_stop_distance)
                            
                            if new_trailing_stop < trailing_stop_price:
                                trailing_stop_price = new_trailing_stop
                                logger.debug(f"Trailing stop CORTO actualizado en {results.index[i]}: nuevo={trailing_stop_price:.2f}")
                        
                        # ORDEN CORRECTO: Verificar stops ANTES de liquidación (para SHORT también)
                        
                        # 0. Verificar TP Parcial (Scaling Out) si está habilitado y no se ha ejecutado
                        # Primero, recalcular TP1 dinámico en cada vela (puede cambiar con volatilidad)
                        if self.tp_dynamic_enabled and not tp_partial_executed and tp1_price > 0:
                            # Recalcular TP1 dinámico usando valores actuales
                            tp1_candidates = []
                            
                            # TP1 basado en ATR (actualizado) - para SHORT, TP1 es hacia abajo
                            if self.tp_atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    tp1_atr = entry_price - (atr_value * self.tp_atr_multiplier)
                                    tp1_candidates.append(tp1_atr)
                            
                            # TP1 basado en VWAP lower band (actualizado) - para shorts
                            if vwap_lower_band is not None:
                                if not pd.isna(vwap_lower_band.iloc[i]):
                                    tp1_vwap = vwap_lower_band.iloc[i]
                                    tp1_candidates.append(tp1_vwap)
                            
                            # Usar el más cercano (más conservador) si hay múltiples candidatos
                            if tp1_candidates:
                                tp1_price = max(tp1_candidates)  # El más cercano (más alto) es más conservador para shorts
                        
                        # Verificar si TP Parcial debe ejecutarse (solo si estamos en ganancia)
                        if (self.tp_dynamic_enabled and not tp_partial_executed and 
                            tp1_price > 0 and tp1_price < entry_price and low <= tp1_price):
                            # Ejecutar cierre parcial
                            partial_position_size = original_position_size * self.tp_partial_pct
                            partial_entry_capital = original_entry_capital * self.tp_partial_pct
                            execution_price = tp1_price
                            
                            # Calcular P&L de la parte parcial (en SHORT, ganamos cuando baja)
                            partial_pnl = partial_position_size * (entry_price - execution_price) * (1 - self.commission)
                            
                            # SOLO ejecutar si hay ganancia real
                            if partial_pnl > 0:
                                # Reducir posición y capital (position es negativo para SHORT, así que sumar reduce el tamaño absoluto)
                                position = position + partial_position_size  # Sumar porque es negativo (reduce tamaño absoluto)
                                entry_capital = entry_capital - partial_entry_capital
                                
                                # El capital disponible incluye lo obtenido del cierre parcial
                                available_capital = partial_entry_capital + partial_pnl
                                
                                # El capital total es el disponible más el valor de la posición restante
                                capital = available_capital + entry_capital
                                
                                # Registrar ganancia del TP parcial para cálculo correcto en get_trades()
                                if current_entry_index is not None:
                                    tp_partial_profits[current_entry_index] = tp_partial_profits.get(current_entry_index, 0) + partial_pnl
                                
                                # Marcar como ejecutado
                                tp_partial_executed = True
                                
                                # Mover stop loss a breakeven (precio de entrada)
                                stop_loss_price = entry_price
                                
                                logger.info(
                                    f"TP Parcial CORTO alcanzado en {results.index[i]}: "
                                    f"Asegurando {self.tp_partial_pct*100:.0f}% de ganancias ({partial_pnl:.2f} USDT), "
                                    f"Stop Loss movido a Breakeven ({entry_price:.2f})"
                                )
                        
                        # 0.5. Verificar EXHAUSTION (verificación independiente, no bloquea otros stops)
                        position_closed_by_exhaustion_short = False
                        if self.exhaustion_exit_enabled and cvd_values is not None and i >= self.exhaustion_lookback:
                            current_profit_pct_ex = (entry_price - price) / entry_price  # En SHORT, ganamos cuando baja
                            # Solo considerar si estamos en ganancia (al menos 2%)
                            if current_profit_pct_ex >= 0.02:
                                exhaustion, reason = self._detect_exhaustion_divergence(
                                    close_prices.iloc[:i+1],
                                    cvd_values.iloc[:i+1],
                                    'SHORT',
                                    lookback=self.exhaustion_lookback
                                )
                                if exhaustion:
                                    # Cerrar posición por exhaustion
                                    execution_price = price
                                    pnl = position_size * (entry_price - execution_price) * (1 - self.commission)
                                    available_capital = entry_capital + pnl
                                    capital = available_capital
                                    if current_entry_index is not None:
                                        trade_exit_reasons[i] = 'EXHAUSTION'
                                    position = 0.0
                                    entry_price = 0.0
                                    entry_capital = 0.0
                                    stop_loss_price = 0.0
                                    take_profit_price = 0.0
                                    trailing_stop_active = False
                                    lowest_price = float('inf')
                                    trailing_stop_price = 0.0
                                    tp_partial_executed = False
                                    original_position_size = 0.0
                                    original_entry_capital = 0.0
                                    tp1_price = 0.0
                                    current_entry_index = None
                                    current_position_type = None
                                    position_closed_by_exhaustion_short = True
                                    logger.info(f"EXHAUSTION SHORT en {results.index[i]}: {reason}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # 1. Verificar trailing stop primero (tiene máxima prioridad) - solo si no se cerró por exhaustion
                        if not position_closed_by_exhaustion_short and trailing_stop_active and high >= trailing_stop_price:
                            execution_price = trailing_stop_price
                            pnl = position_size * (entry_price - execution_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            # Rastrear exit_reason antes de resetear variables
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'TRAILING_STOP'
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            lowest_price = float('inf')
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            current_entry_index = None
                            current_position_type = None
                            logger.info(f"Cierre CORTO: Trailing Stop en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # 2. Verificar stop loss ANTES de liquidación (usando high para detectar si se tocó en la vela)
                        elif not position_closed_by_exhaustion_short and stop_loss_price > 0 and high >= stop_loss_price:
                            # Stop loss corto activado (precio subió hasta el stop loss o más)
                            # Usar el precio del stop loss como precio de ejecución
                            execution_price = stop_loss_price
                            # P&L en corto: (precio_entrada - precio_salida) * cantidad
                            pnl = position_size * (entry_price - execution_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            # Rastrear exit_reason antes de resetear variables
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'STOP_LOSS'
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            lowest_price = float('inf')
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            current_entry_index = None
                            current_position_type = None
                            logger.info(f"Cierre CORTO: Stop Loss en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # Verificar take profit corto (usando low para detectar si se tocó en la vela)
                        elif not position_closed_by_exhaustion_short and self.take_profit_pct is not None and low <= take_profit_price:
                            # Take profit corto activado (precio bajó hasta el take profit o más)
                            # Usar el precio del take profit como precio de ejecución
                            execution_price = take_profit_price
                            pnl = position_size * (entry_price - execution_price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            capital = available_capital
                            # Rastrear exit_reason antes de resetear variables
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'TAKE_PROFIT'
                            position = 0.0
                            entry_price = 0.0
                            entry_capital = 0.0
                            stop_loss_price = 0.0
                            take_profit_price = 0.0
                            trailing_stop_active = False
                            lowest_price = float('inf')
                            trailing_stop_price = 0.0
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = 0.0
                            original_entry_capital = 0.0
                            tp1_price = 0.0
                            current_entry_index = None
                            current_position_type = None
                            logger.info(f"Cierre CORTO: Take Profit en {results.index[i]}: precio ejecución={execution_price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                
                # Ejecutar operaciones según la señal
                if signal == 1:  # Señal de compra/largo
                    if position == 0:
                        # Abrir posición larga (spot o futures)
                        # Usar TODO el capital disponible (método original)
                        entry_capital = available_capital
                        position_size = (entry_capital * self.leverage) / price * (1 - self.commission)
                        position = position_size
                        entry_price = price
                        capital = available_capital - entry_capital  # Capital restante (será 0)
                        available_capital = 0  # Todo el capital está en la posición
                        
                        # Rastrear índice de entrada de la posición actual
                        current_entry_index = i
                        current_position_type = 'LONG'
                        
                        # Resetear variables de trailing stop
                        trailing_stop_active = False
                        highest_price = price
                        trailing_stop_price = 0.0
                        
                        # Resetear variables de Scaling Out
                        tp_partial_executed = False
                        original_position_size = position_size
                        original_entry_capital = entry_capital
                        tp1_price = 0.0
                        
                        # Calcular TP1 dinámico si está habilitado
                        if self.tp_dynamic_enabled and self.tp_partial_pct is not None:
                            # Calcular TP1 usando ATR o VWAP bands
                            tp1_candidates = []
                            
                            # TP1 basado en ATR
                            if self.tp_atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    tp1_atr = entry_price + (atr_value * self.tp_atr_multiplier)
                                    tp1_candidates.append(tp1_atr)
                            
                            # TP1 basado en VWAP upper band (para longs)
                            if vwap_upper_band is not None:
                                if not pd.isna(vwap_upper_band.iloc[i]):
                                    tp1_vwap = vwap_upper_band.iloc[i]
                                    tp1_candidates.append(tp1_vwap)
                            
                            # Usar el más cercano (más conservador) si hay múltiples candidatos
                            if tp1_candidates:
                                tp1_price = min(tp1_candidates)  # El más cercano es más conservador para longs
                                logger.debug(f"TP1 dinámico LARGO calculado: {tp1_price:.2f} (entry: {entry_price:.2f})")
                        
                        # Establecer stop loss y take profit para largo
                        # Usar ATR como stop dinámico principal y stop_loss_pct como hard stop de emergencia
                        # Para LONG: usar el más conservador (más alto = más cerca del precio de entrada)
                        atr_stop = None
                        hard_stop = None
                        
                        if self.atr_period is not None and self.atr_multiplier is not None and atr_values is not None:
                            if not pd.isna(atr_values.iloc[i]):
                                atr_value = atr_values.iloc[i]
                                atr_stop = entry_price - (atr_value * self.atr_multiplier)
                        
                        if self.stop_loss_pct is not None:
                            hard_stop = entry_price * (1 - self.stop_loss_pct)
                        
                        # Hard stop de emergencia (si está activado y no hay hard_stop definido)
                        emergency_stop = None
                        if self.emergency_stop_pct is not None:
                            emergency_stop = entry_price * (1 - self.emergency_stop_pct)
                        
                        # Usar el más conservador (más alto para LONG = más cerca del precio)
                        # Orden de prioridad: hard_stop (si existe) > emergency_stop > atr_stop
                        stops = [s for s in [hard_stop, emergency_stop, atr_stop] if s is not None]
                        if stops:
                            stop_loss_price = max(stops)  # El más alto es más conservador
                            atr_str = f"{atr_stop:.2f}" if atr_stop else "None"
                            hard_str = f"{hard_stop:.2f}" if hard_stop else "None"
                            emerg_str = f"{emergency_stop:.2f}" if emergency_stop else "None"
                            logger.debug(f"LONG: ATR={atr_str}, Hard={hard_str}, Emerg={emerg_str}, Usando={stop_loss_price:.2f}")
                        else:
                            stop_loss_price = entry_price * 0.98  # Fallback
                        if self.take_profit_pct is not None:
                            take_profit_price = entry_price * (1 + self.take_profit_pct)
                        
                        logger.debug(f"Compra/LARGO abierto en {results.index[i]}: precio={price:.2f}, posición={position:.6f}, leverage={self.leverage}x")
                    
                    elif position < 0 and self.market_type == 'futures':
                        # Validar volumen antes de ejecutar reversión (corto -> largo)
                        volume_valid = True
                        if self.volume_reversal_period is not None and self.volume_reversal_threshold is not None and volume_data is not None:
                            if i >= self.volume_reversal_period:
                                volume_ma = volume_data.iloc[i - self.volume_reversal_period + 1:i + 1].mean()
                                current_volume = volume_data.iloc[i]
                                volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
                                volume_valid = volume_ratio >= self.volume_reversal_threshold
                                if not volume_valid:
                                    logger.debug(f"Reversión bloqueada por volumen insuficiente: ratio={volume_ratio:.2f}, threshold={self.volume_reversal_threshold}")
                        
                        if volume_valid:
                            # Cerrar corto y abrir largo (reversión en futures)
                            position_size = abs(position)
                            # Cerrar corto: recuperar capital + P&L
                            pnl = position_size * (entry_price - price) * (1 - self.commission)
                            available_capital = entry_capital + pnl
                            # Rastrear exit_reason antes de abrir nueva posición
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'SIGNAL'
                            # Abrir largo con el nuevo capital disponible
                            entry_capital = available_capital
                            position_size_new = (entry_capital * self.leverage) / price * (1 - self.commission)
                            position = position_size_new
                            entry_price = price
                            capital = 0
                            available_capital = 0
                            
                            # Rastrear índice de entrada de la nueva posición
                            current_entry_index = i
                            current_position_type = 'LONG'
                            
                            # Resetear variables de trailing stop
                            trailing_stop_active = False
                            highest_price = price
                            trailing_stop_price = 0.0
                            
                            # Establecer stop loss y take profit para nuevo largo
                            # Prioridad: hard_stop > emergency_stop > atr_stop (el más conservador para LONG = el más alto)
                            atr_stop = None
                            hard_stop = None
                            emergency_stop = None
                            if self.atr_period is not None and self.atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    atr_stop = entry_price - (atr_value * self.atr_multiplier)
                            if self.stop_loss_pct is not None:
                                hard_stop = entry_price * (1 - self.stop_loss_pct)
                            if self.emergency_stop_pct is not None:
                                emergency_stop = entry_price * (1 - self.emergency_stop_pct)
                            # Orden de prioridad: hard_stop (si existe) > emergency_stop > atr_stop
                            stops = [s for s in [hard_stop, emergency_stop, atr_stop] if s is not None]
                            if stops:
                                stop_loss_price = max(stops)  # El más alto es más conservador para LONG
                                atr_str = f"{atr_stop:.2f}" if atr_stop else "None"
                                hard_str = f"{hard_stop:.2f}" if hard_stop else "None"
                                emerg_str = f"{emergency_stop:.2f}" if emergency_stop else "None"
                                logger.debug(f"LONG (reversión): ATR={atr_str}, Hard={hard_str}, Emerg={emerg_str}, Usando={stop_loss_price:.2f}")
                            else:
                                stop_loss_price = entry_price * 0.98
                            if self.take_profit_pct is not None:
                                take_profit_price = entry_price * (1 + self.take_profit_pct)
                            
                            logger.debug(f"Reversión: Corto cerrado, LARGO abierto en {results.index[i]}: precio={price:.2f}, leverage={self.leverage}x")
                
                elif signal == -1:  # Señal de venta
                    if position > 0:
                        # Cerrar posición larga (spot y futures)
                        # Con leverage: recuperamos capital inicial + P&L
                        pnl = position * (price - entry_price) * (1 - self.commission)
                        available_capital = entry_capital + pnl
                        capital = available_capital
                        # Rastrear exit_reason antes de resetear variables
                        if current_entry_index is not None:
                            trade_exit_reasons[i] = 'SIGNAL'
                        position = 0.0
                        entry_price = 0.0
                        entry_capital = 0.0
                        stop_loss_price = 0.0
                        take_profit_price = 0.0
                        current_entry_index = None
                        current_position_type = None
                        logger.info(f"Cierre LARGO: Señal en {results.index[i]}: precio={price:.2f}, capital={capital:.2f}, P&L={pnl:.2f} USDT")
                        
                        # En futuros, después de cerrar largo con señal de venta, abrir corto
                        # Validar volumen antes de ejecutar reversión (largo -> corto)
                        volume_valid = True
                        if self.market_type == 'futures':
                            if self.volume_reversal_period is not None and self.volume_reversal_threshold is not None and volume_data is not None:
                                if i >= self.volume_reversal_period:
                                    volume_ma = volume_data.iloc[i - self.volume_reversal_period + 1:i + 1].mean()
                                    current_volume = volume_data.iloc[i]
                                    volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
                                    volume_valid = volume_ratio >= self.volume_reversal_threshold
                                    if not volume_valid:
                                        logger.debug(f"Reversión bloqueada por volumen insuficiente: ratio={volume_ratio:.2f}, threshold={self.volume_reversal_threshold}")
                        
                        if self.market_type == 'futures' and volume_valid:
                            # Abrir corto con todo el capital disponible
                            entry_capital = available_capital
                            position_size = (entry_capital * self.leverage) / price * (1 - self.commission)
                            position = -position_size  # Negativo para indicar corto
                            entry_price = price
                            capital = 0
                            available_capital = 0
                            
                            # Rastrear índice de entrada de la posición actual
                            current_entry_index = i
                            current_position_type = 'SHORT'
                            
                            # Resetear variables de trailing stop
                            trailing_stop_active = False
                            lowest_price = price
                            trailing_stop_price = 0.0
                            
                            # Resetear variables de Scaling Out
                            tp_partial_executed = False
                            original_position_size = position_size
                            original_entry_capital = entry_capital
                            tp1_price = 0.0
                            
                            # Calcular TP1 dinámico si está habilitado (para SHORT)
                            if self.tp_dynamic_enabled and self.tp_partial_pct is not None:
                                tp1_candidates = []
                                
                                # TP1 basado en ATR (para SHORT, TP1 es hacia abajo)
                                if self.tp_atr_multiplier is not None and atr_values is not None:
                                    if not pd.isna(atr_values.iloc[i]):
                                        atr_value = atr_values.iloc[i]
                                        tp1_atr = entry_price - (atr_value * self.tp_atr_multiplier)
                                        tp1_candidates.append(tp1_atr)
                                
                                # TP1 basado en VWAP lower band (para shorts)
                                if vwap_lower_band is not None:
                                    if not pd.isna(vwap_lower_band.iloc[i]):
                                        tp1_vwap = vwap_lower_band.iloc[i]
                                        tp1_candidates.append(tp1_vwap)
                                
                                # Usar el más cercano (más conservador) si hay múltiples candidatos
                                if tp1_candidates:
                                    tp1_price = max(tp1_candidates)  # El más cercano (más alto) es más conservador para shorts
                                    logger.debug(f"TP1 dinámico CORTO calculado: {tp1_price:.2f} (entry: {entry_price:.2f})")
                            
                            # Establecer stop loss y take profit para corto
                            # En corto: stop loss se activa cuando precio SUBE
                            # Prioridad: hard_stop > emergency_stop > atr_stop (el más conservador para SHORT = el más bajo)
                            atr_stop = None
                            hard_stop = None
                            emergency_stop = None
                            if self.atr_period is not None and self.atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    atr_stop = entry_price + (atr_value * self.atr_multiplier)
                            if self.stop_loss_pct is not None:
                                hard_stop = entry_price * (1 + self.stop_loss_pct)
                            if self.emergency_stop_pct is not None:
                                emergency_stop = entry_price * (1 + self.emergency_stop_pct)
                            # Orden de prioridad: hard_stop (si existe) > emergency_stop > atr_stop
                            # Para SHORT: usar el más conservador (más bajo = más cerca del precio)
                            stops = [s for s in [hard_stop, emergency_stop, atr_stop] if s is not None]
                            if stops:
                                stop_loss_price = min(stops)  # El más bajo es más conservador para SHORT
                                atr_str = f"{atr_stop:.2f}" if atr_stop else "None"
                                hard_str = f"{hard_stop:.2f}" if hard_stop else "None"
                                emerg_str = f"{emergency_stop:.2f}" if emergency_stop else "None"
                                logger.debug(f"SHORT: ATR={atr_str}, Hard={hard_str}, Emerg={emerg_str}, Usando={stop_loss_price:.2f}")
                            else:
                                stop_loss_price = entry_price * 1.02
                            # En corto: take profit se activa cuando precio BAJA
                            if self.take_profit_pct is not None:
                                take_profit_price = entry_price * (1 - self.take_profit_pct)
                            
                            logger.debug(f"CORTO abierto (después de cerrar largo) en {results.index[i]}: precio={price:.2f}, posición={position:.6f}, leverage={self.leverage}x")
                    
                    elif position == 0 and self.market_type == 'futures':
                        # Abrir posición corta (solo en futures)
                        entry_capital = available_capital
                        position_size = (entry_capital * self.leverage) / price * (1 - self.commission)
                        position = -position_size  # Negativo para indicar corto
                        entry_price = price
                        capital = 0
                        available_capital = 0
                        
                        # Rastrear índice de entrada de la posición actual
                        current_entry_index = i
                        current_position_type = 'SHORT'
                        
                        # Resetear variables de trailing stop
                        trailing_stop_active = False
                        lowest_price = price
                        trailing_stop_price = 0.0
                        
                        # Resetear variables de Scaling Out
                        tp_partial_executed = False
                        original_position_size = abs(position_size)
                        original_entry_capital = entry_capital
                        tp1_price = 0.0
                        
                        # Calcular TP1 dinámico si está habilitado (para SHORT)
                        if self.tp_dynamic_enabled and self.tp_partial_pct is not None:
                            tp1_candidates = []
                            
                            # TP1 basado en ATR (para SHORT, TP1 es hacia abajo)
                            if self.tp_atr_multiplier is not None and atr_values is not None:
                                if not pd.isna(atr_values.iloc[i]):
                                    atr_value = atr_values.iloc[i]
                                    tp1_atr = entry_price - (atr_value * self.tp_atr_multiplier)
                                    tp1_candidates.append(tp1_atr)
                            
                            # TP1 basado en VWAP lower band (para shorts)
                            if vwap_lower_band is not None:
                                if not pd.isna(vwap_lower_band.iloc[i]):
                                    tp1_vwap = vwap_lower_band.iloc[i]
                                    tp1_candidates.append(tp1_vwap)
                            
                            # Usar el más cercano (más conservador) si hay múltiples candidatos
                            if tp1_candidates:
                                tp1_price = max(tp1_candidates)  # El más cercano (más alto) es más conservador para shorts
                                logger.debug(f"TP1 dinámico CORTO calculado: {tp1_price:.2f} (entry: {entry_price:.2f})")
                        
                        # Establecer stop loss y take profit para corto
                        # En corto: stop loss se activa cuando precio SUBE
                        atr_stop = None
                        hard_stop = None
                        if self.atr_period is not None and self.atr_multiplier is not None and atr_values is not None:
                            if not pd.isna(atr_values.iloc[i]):
                                atr_value = atr_values.iloc[i]
                                atr_stop = entry_price + (atr_value * self.atr_multiplier)
                        if self.stop_loss_pct is not None:
                            hard_stop = entry_price * (1 + self.stop_loss_pct)
                        if atr_stop is not None and hard_stop is not None:
                            stop_loss_price = min(atr_stop, hard_stop)
                        elif atr_stop is not None:
                            stop_loss_price = atr_stop
                        elif hard_stop is not None:
                            stop_loss_price = hard_stop
                        else:
                            stop_loss_price = entry_price * 1.02
                        # En corto: take profit se activa cuando precio BAJA
                        if self.take_profit_pct is not None:
                            take_profit_price = entry_price * (1 - self.take_profit_pct)
                        
                        logger.debug(f"CORTO abierto en {results.index[i]}: precio={price:.2f}, posición={position:.6f}, leverage={self.leverage}x")
                    
                    elif position < 0 and self.market_type == 'futures':
                        # Cerrar corto y abrir nuevo corto (re-apertura)
                        position_size = abs(position)
                        # Cerrar corto anterior: recuperar capital + P&L
                        pnl = position_size * (entry_price - price) * (1 - self.commission)
                        available_capital = entry_capital + pnl
                        # Rastrear exit_reason antes de abrir nueva posición
                        if current_entry_index is not None:
                            trade_exit_reasons[i] = 'SIGNAL'
                        # Abrir nuevo corto
                        entry_capital = available_capital
                        position_size_new = (entry_capital * self.leverage) / price * (1 - self.commission)
                        position = -position_size_new
                        entry_price = price
                        capital = 0
                        available_capital = 0
                        
                        # Rastrear índice de entrada de la nueva posición
                        current_entry_index = i
                        current_position_type = 'SHORT'
                        
                        # Resetear variables de trailing stop
                        trailing_stop_active = False
                        lowest_price = price
                        trailing_stop_price = 0.0
                        
                        # Establecer stop loss y take profit para nuevo corto
                        atr_stop = None
                        hard_stop = None
                        if self.atr_period is not None and self.atr_multiplier is not None and atr_values is not None:
                            if not pd.isna(atr_values.iloc[i]):
                                atr_value = atr_values.iloc[i]
                                atr_stop = entry_price + (atr_value * self.atr_multiplier)
                        if self.stop_loss_pct is not None:
                            hard_stop = entry_price * (1 + self.stop_loss_pct)
                        if atr_stop is not None and hard_stop is not None:
                            stop_loss_price = min(atr_stop, hard_stop)
                        elif atr_stop is not None:
                            stop_loss_price = atr_stop
                        elif hard_stop is not None:
                            stop_loss_price = hard_stop
                        else:
                            stop_loss_price = entry_price * 1.02
                        if self.take_profit_pct is not None:
                            take_profit_price = entry_price * (1 - self.take_profit_pct)
                        
                        logger.debug(f"CORTO reabierto en {results.index[i]}: precio={price:.2f}, leverage={self.leverage}x")
                
                # Calcular valor actual del portfolio
                if position > 0:
                    # Largo con leverage: valor = capital_inicial + P&L
                    pnl = position * (price - entry_price) if entry_price > 0 else 0
                    portfolio_value = max(0.0, entry_capital + pnl) if entry_price > 0 else capital
                    # Verificación adicional de liquidación (backup, ya se verifica antes)
                    if portfolio_value <= 0.0 and entry_capital > 0 and (len(liquidation_events) == 0 or (len(liquidation_events) > 0 and liquidation_events[-1]['timestamp'] != results.index[i])):
                        logger.warning(f"Liquidación LARGO detectada (backup) en {results.index[i]}: equity={portfolio_value:.2f}")
                        if len(liquidation_events) == 0 or liquidation_events[-1]['timestamp'] != results.index[i]:
                            liquidation_events.append({
                                'timestamp': results.index[i],
                                'type': 'LONG',
                                'entry_price': entry_price,
                                'liquidation_price': price,
                                'equity': portfolio_value,
                                'entry_capital': entry_capital,
                                'pnl': pnl
                            })
                            # Rastrear exit_reason para liquidación
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'LIQUIDATION'
                        capital = 0.0
                        available_capital = 0.0
                        position = 0.0
                        entry_price = 0.0
                        entry_capital = 0.0
                        current_entry_index = None
                        current_position_type = None
                elif position < 0:
                    # Corto con leverage: valor = capital_inicial + P&L
                    position_size = abs(position)
                    pnl = position_size * (entry_price - price) if entry_price > 0 else 0
                    portfolio_value = max(0.0, entry_capital + pnl) if entry_price > 0 else capital
                    # Verificación adicional de liquidación (backup)
                    if portfolio_value <= 0.0 and entry_capital > 0 and (len(liquidation_events) == 0 or liquidation_events[-1]['timestamp'] != results.index[i]):
                        logger.warning(f"Liquidación CORTO detectada (backup) en {results.index[i]}: equity={portfolio_value:.2f}")
                        if len(liquidation_events) == 0 or liquidation_events[-1]['timestamp'] != results.index[i]:
                            liquidation_events.append({
                                'timestamp': results.index[i],
                                'type': 'SHORT',
                                'entry_price': entry_price,
                                'liquidation_price': price,
                                'equity': portfolio_value,
                                'entry_capital': entry_capital,
                                'pnl': pnl
                            })
                            # Rastrear exit_reason para liquidación
                            if current_entry_index is not None:
                                trade_exit_reasons[i] = 'LIQUIDATION'
                        capital = 0.0
                        available_capital = 0.0
                        position = 0.0
                        entry_price = 0.0
                        entry_capital = 0.0
                        current_entry_index = None
                        current_position_type = None
                else:
                    portfolio_value = capital
                
                # Calcular retornos
                if i == 0:
                    results.iloc[i, results.columns.get_loc('returns')] = 0.0
                    results.iloc[i, results.columns.get_loc('cumulative_returns')] = 0.0
                else:
                    # Usar el valor del portfolio del período anterior
                    prev_value = results['capital'].iloc[i-1]
                    current_value = portfolio_value
                    period_return = (current_value - prev_value) / prev_value if prev_value > 0 else 0.0
                    results.iloc[i, results.columns.get_loc('returns')] = period_return
                    
                    cumulative = (portfolio_value - self.initial_capital) / self.initial_capital
                    # Limitar cumulative returns a -1.0 (máxima pérdida posible = 100%)
                    cumulative = max(cumulative, -1.0)
                    results.iloc[i, results.columns.get_loc('cumulative_returns')] = cumulative
                
                results.iloc[i, results.columns.get_loc('position')] = position
                # Guardar el valor del portfolio (capital en efectivo o valor de la posición)
                results.iloc[i, results.columns.get_loc('capital')] = portfolio_value
            
            # Guardar eventos de liquidación en atributo para acceso posterior
            self.liquidation_events = liquidation_events
            
            # Guardar trade_exit_reasons y tp_partial_profits en atributos para uso en get_trades
            self.trade_exit_reasons = trade_exit_reasons
            self.tp_partial_profits = tp_partial_profits
            
            if liquidation_events:
                logger.warning(f"⚠️ Se detectaron {len(liquidation_events)} liquidación(es) durante el backtest")
                for liq in liquidation_events:
                    logger.warning(f"   - {liq['type']} en {liq['timestamp']}: entrada={liq['entry_price']:.2f}, liquidación={liq['liquidation_price']:.2f}, pérdida={liq['pnl']:.2f}")
            else:
                logger.info("✅ No se detectaron liquidaciones durante el backtest")
            
            logger.info("Backtest completado exitosamente")
            return results
            
        except BacktesterError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado al ejecutar backtest: {e}")
            raise BacktesterError(f"Error al ejecutar backtest: {e}")
    
    def calculate_metrics(self, results: pd.DataFrame, timeframe: str = '1d') -> Dict[str, Any]:
        """
        Calcula métricas de rendimiento del backtest.
        
        Args:
            results: DataFrame retornado por run_backtest.
            timeframe: Timeframe usado para ajustar cálculos anualizados (por defecto '1d').
            
        Returns:
            Diccionario con las métricas calculadas.
            
        Raises:
            BacktesterError: Si hay error al calcular métricas.
        """
        try:
            if results.empty:
                raise BacktesterError("El DataFrame de resultados está vacío")
            
            if 'returns' not in results.columns or 'capital' not in results.columns:
                raise BacktesterError("El DataFrame debe contener las columnas 'returns' y 'capital'")
            
            # Valor final del portfolio
            final_position = results['position'].iloc[-1]
            final_price = results['close'].iloc[-1]
            final_capital = results['capital'].iloc[-1]
            
            # El capital ya incluye el P&L acumulado y el valor de la posición (calculado en cada iteración)
            # Por lo tanto, simplemente usamos el capital final directamente
            final_value = final_capital
            
            # Retorno total
            total_return = (final_value - self.initial_capital) / self.initial_capital
            
            # Retornos periódicos (eliminar NaN y ceros iniciales)
            returns = results['returns'].dropna()
            if len(returns) == 0:
                returns = pd.Series([0.0])
            
            # Calcular períodos por año según timeframe
            periods_per_year = self._get_periods_per_year(timeframe)
            
            # Retorno promedio anualizado
            num_periods = len(returns)
            if num_periods > 0:
                avg_return = returns.mean()
                annualized_return = avg_return * periods_per_year
            else:
                annualized_return = 0.0
            
            # Sharpe Ratio (asumiendo risk-free rate = 0)
            if len(returns) > 1 and returns.std() > 0:
                sharpe_ratio = np.sqrt(periods_per_year) * (returns.mean() / returns.std())
            else:
                sharpe_ratio = 0.0
            
            # Maximum Drawdown
            cumulative_returns = results['cumulative_returns']
            # Asegurar que cumulative_returns no sea menor que -1.0 (100% de pérdida máxima)
            cumulative_returns = cumulative_returns.clip(lower=-1.0)
            running_max = cumulative_returns.expanding().max()
            drawdown = cumulative_returns - running_max
            max_drawdown = drawdown.min()
            # El drawdown no puede ser menor que -1.0 (100% de pérdida)
            max_drawdown = max(max_drawdown, -1.0)
            
            # Número de operaciones
            signals = results['signal']
            num_trades = ((signals == 1) | (signals == -1)).sum()
            num_buy_trades = (signals == 1).sum()
            num_sell_trades = (signals == -1).sum()
            
            # Calcular win rate y profit factor
            win_rate, profit_factor, avg_win, avg_loss = self._calculate_trade_stats(results)
            
            # Métricas de liquidaciones
            num_liquidations = len(getattr(self, 'liquidation_events', []))
            liquidation_rate = num_liquidations / num_trades if num_trades > 0 else 0.0
            
            metrics = {
                'initial_capital': self.initial_capital,
                'final_value': final_value,
                'final_capital': final_value,  # Alias para compatibilidad
                'total_return': total_return,
                'total_return_pct': total_return * 100,
                'annualized_return': annualized_return,
                'annualized_return_pct': annualized_return * 100,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown * 100,
                'num_trades': num_trades,
                'num_buy_trades': num_buy_trades,
                'num_sell_trades': num_sell_trades,
                'volatility': returns.std() * np.sqrt(periods_per_year) if len(returns) > 1 else 0.0,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'num_liquidations': num_liquidations,
                'liquidation_rate': liquidation_rate,
                'has_liquidation': num_liquidations > 0
            }
            
            logger.info(f"Métricas calculadas: Retorno={total_return*100:.2f}%, Sharpe={sharpe_ratio:.2f}, MaxDD={max_drawdown*100:.2f}%")
            
            return metrics
            
        except BacktesterError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado al calcular métricas: {e}")
            raise BacktesterError(f"Error al calcular métricas: {e}")
    
    def calculate_dynamic_position_size(
        self,
        available_capital: float,
        entry_price: float,
        atr_value: float = None,
        risk_pct: float = 0.02,
        recent_performance: Dict[str, int] = None
    ) -> Tuple[float, float]:
        """
        Calcula tamaño de posición dinámico basado en ATR para mantener riesgo constante.
        
        Args:
            available_capital: Capital disponible para la operación.
            entry_price: Precio de entrada.
            atr_value: Valor de ATR actual (opcional).
            risk_pct: Porcentaje de capital a arriesgar por operación (default: 2%).
            recent_performance: Dict con 'wins' y 'losses' para ajustar tamaño según performance.
            
        Returns:
            Tupla (position_size, entry_capital).
        """
        # Ajustar risk_pct según performance reciente si se proporciona
        adjusted_risk_pct = risk_pct
        if recent_performance:
            wins = recent_performance.get('wins', 0)
            losses = recent_performance.get('losses', 0)
            total_trades = wins + losses
            if total_trades > 0:
                win_rate_recent = wins / total_trades
                # Reducir tamaño si win rate reciente es bajo
                if win_rate_recent < 0.4:
                    adjusted_risk_pct = risk_pct * 0.5  # Reducir a la mitad
                elif win_rate_recent < 0.5:
                    adjusted_risk_pct = risk_pct * 0.75  # Reducir un 25%
        
        # Calcular monto de riesgo
        risk_amount = available_capital * adjusted_risk_pct
        
        # Si hay ATR, usar para calcular stop distance
        if atr_value is not None and atr_value > 0:
            # Usar ATR multiplicado por el multiplier para stop distance
            atr_multiplier = self.atr_multiplier if self.atr_multiplier is not None else 1.5
            stop_distance = atr_value * atr_multiplier
            # Calcular position size basado en riesgo y stop distance
            position_size_by_risk = risk_amount / stop_distance
        else:
            # Fallback: usar stop_loss_pct si está disponible
            if self.stop_loss_pct is not None:
                stop_distance = entry_price * self.stop_loss_pct
                position_size_by_risk = risk_amount / stop_distance
            else:
                # Sin ATR ni stop_loss_pct, usar método tradicional
                stop_distance = entry_price * 0.03  # Asumir 3% de stop
                position_size_by_risk = risk_amount / stop_distance
        
        # Calcular position size máximo por leverage
        max_position_size = (available_capital * self.leverage) / entry_price * (1 - self.commission)
        
        # Usar el menor entre position size por riesgo y máximo por leverage
        position_size = min(position_size_by_risk, max_position_size)
        
        # Calcular entry_capital necesario
        entry_capital = (position_size * entry_price) / self.leverage / (1 - self.commission)
        
        # Asegurar que entry_capital no exceda available_capital
        entry_capital = min(entry_capital, available_capital)
        
        # Recalcular position_size con entry_capital ajustado
        position_size = (entry_capital * self.leverage) / entry_price * (1 - self.commission)
        
        return position_size, entry_capital
    
    def _get_periods_per_year(self, timeframe: str) -> float:
        """
        Calcula el número de períodos por año según el timeframe.
        
        Args:
            timeframe: Timeframe (ej: '1d', '4h', '1h', '15m').
            
        Returns:
            Número de períodos por año.
        """
        timeframe_map = {
            '1m': 525600,   # minutos en un año
            '5m': 105120,
            '15m': 35040,
            '1h': 8760,
            '4h': 2190,
            '1d': 365,
            '1w': 52,
            '1M': 12
        }
        
        # Intentar encontrar el timeframe exacto
        if timeframe in timeframe_map:
            return timeframe_map[timeframe]
        
        # Si no se encuentra, intentar extraer el número y la unidad
        # Por ejemplo, '2h' -> 2 horas
        import re
        match = re.match(r'(\d+)([mhdwM])', timeframe)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            base_periods = {
                'm': 525600,  # minutos
                'h': 8760,    # horas
                'd': 365,     # días
                'w': 52,      # semanas
                'M': 12       # meses
            }
            if unit in base_periods:
                return base_periods[unit] / number
        
        # Por defecto, asumir días
        logger.warning(f"Timeframe '{timeframe}' no reconocido, usando 365 períodos/año")
        return 365.0
    
    def _calculate_trade_stats(self, results: pd.DataFrame) -> tuple:
        """
        Calcula estadísticas de operaciones: win rate, profit factor, etc.
        
        Usa get_trades() para obtener TODAS las operaciones, incluyendo las cerradas
        con stops, trailing stops, TP parcial, liquidaciones, etc.
        
        Args:
            results: DataFrame con los resultados del backtest.
            
        Returns:
            Tupla con (win_rate, profit_factor, avg_win, avg_loss).
        """
        # Usar get_trades() que rastrea correctamente TODAS las operaciones
        # (incluyendo cierres por stops, trailing stops, TP parcial, liquidaciones)
        trades_df = self.get_trades(results)
        
        if trades_df.empty:
            return 0.0, 0.0, 0.0, 0.0
        
        # Obtener P&L en porcentaje de cada operación
        # P&L (%) ya está calculado considerando comisiones y leverage en get_trades
        trades_pnl_pct = trades_df['P&L (%)'].values / 100.0  # Convertir de porcentaje a fracción
        
        # Calcular win rate basado en P&L real
        winning_trades = [pnl for pnl in trades_pnl_pct if pnl > 0]
        losing_trades = [pnl for pnl in trades_pnl_pct if pnl < 0]
        win_rate = len(winning_trades) / len(trades_pnl_pct) if len(trades_pnl_pct) > 0 else 0.0
        
        # Calcular profit factor
        total_wins = sum(winning_trades) if winning_trades else 0.0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0.0)
        
        # Calcular promedios
        avg_win = np.mean(winning_trades) * 100 if winning_trades else 0.0
        avg_loss = np.mean(losing_trades) * 100 if losing_trades else 0.0
        
        return win_rate, profit_factor, avg_win, avg_loss
    
    def get_trades(self, results: pd.DataFrame) -> pd.DataFrame:
        """
        Extrae todas las operaciones realizadas durante el backtest.
        
        Args:
            results: DataFrame con los resultados del backtest.
            
        Returns:
            DataFrame con las operaciones (fecha entrada, fecha salida, tipo, precio entrada, precio salida, P&L, capital).
        """
        trades = []
        positions = results['position']
        closes = results['close']
        capital_values = results['capital']
        
        in_position = False
        entry_index = None
        entry_price = 0.0
        entry_capital = 0.0
        position_type = None  # 'LONG' o 'SHORT'
        
        for i in range(len(positions)):
            curr_position = positions.iloc[i]
            price = closes.iloc[i]
            timestamp = results.index[i]
            capital = capital_values.iloc[i]
            
            # Detectar apertura de posición
            if not in_position:
                if curr_position > 0:  # Apertura de largo
                    in_position = True
                    entry_index = i
                    entry_price = price
                    entry_capital = capital
                    position_type = 'LONG'
                elif curr_position < 0:  # Apertura de corto
                    in_position = True
                    entry_index = i
                    entry_price = price
                    entry_capital = capital
                    position_type = 'SHORT'
            else:
                # Detectar cierre de posición
                if (position_type == 'LONG' and curr_position <= 0) or (position_type == 'SHORT' and curr_position >= 0):
                    exit_price = price
                    exit_capital = capital
                    
                    # Calcular P&L incluyendo ganancias de TP parcial si las hubo
                    tp_partial_profit = self.tp_partial_profits.get(entry_index, 0) if hasattr(self, 'tp_partial_profits') else 0
                    
                    # P&L absoluto = (capital final - capital inicial) + ganancias de TP parcial
                    pnl_abs = (exit_capital - entry_capital) + tp_partial_profit
                    pnl_pct = (pnl_abs / entry_capital) * 100 if entry_capital > 0 else 0.0
                    
                    # Obtener exit_reason si está disponible
                    exit_reason = self.trade_exit_reasons.get(i, 'UNKNOWN')
                    
                    trades.append({
                        'Fecha Entrada': results.index[entry_index],
                        'Fecha Salida': timestamp,
                        'Tipo': position_type,
                        'Precio Entrada': entry_price,
                        'Precio Salida': exit_price,
                        'P&L ($)': pnl_abs,
                        'P&L (%)': pnl_pct,
                        'Capital Final': exit_capital,
                        'Exit Reason': exit_reason
                    })
                    
                    in_position = False
                    entry_index = None
                    entry_price = 0.0
                    entry_capital = 0.0
                    position_type = None
                    
                    # Si hay nueva posición, iniciarla
                    if curr_position > 0:
                        in_position = True
                        entry_index = i
                        entry_price = price
                        entry_capital = capital
                        position_type = 'LONG'
                    elif curr_position < 0:
                        in_position = True
                        entry_index = i
                        entry_price = price
                        entry_capital = capital
                        position_type = 'SHORT'
        
        # Si queda posición abierta al final, cerrarla
        if in_position and entry_index is not None:
            exit_price = closes.iloc[-1]
            exit_capital = capital_values.iloc[-1]
            
            # Incluir ganancias de TP parcial si las hubo
            tp_partial_profit = self.tp_partial_profits.get(entry_index, 0) if hasattr(self, 'tp_partial_profits') else 0
            
            pnl_abs = (exit_capital - entry_capital) + tp_partial_profit
            pnl_pct = (pnl_abs / entry_capital) * 100 if entry_capital > 0 else 0.0
            
            # Obtener exit_reason si está disponible (posición cerrada al final del período)
            exit_index = len(results) - 1
            exit_reason = self.trade_exit_reasons.get(exit_index, 'END_OF_PERIOD')
            
            trades.append({
                'Fecha Entrada': results.index[entry_index],
                'Fecha Salida': results.index[-1],
                'Tipo': position_type,
                'Precio Entrada': entry_price,
                'Precio Salida': exit_price,
                'P&L ($)': pnl_abs,
                'P&L (%)': pnl_pct,
                'Capital Final': exit_capital,
                'Exit Reason': exit_reason
            })
        
        return pd.DataFrame(trades)
    
    def save_to_database(
        self,
        db_session,
        backtest_run_id: int,
        results: pd.DataFrame,
        data: pd.DataFrame,
        signals: pd.Series,
        metrics: Dict[str, Any],
        strategy_config: Optional[Any] = None
    ) -> None:
        """
        Guarda los resultados del backtest en la base de datos.
        
        Args:
            db_session: Sesión de base de datos SQLAlchemy.
            backtest_run_id: ID del registro BacktestRun en la BD.
            results: DataFrame con resultados del backtest.
            data: DataFrame con datos de mercado originales.
            signals: Series con señales generadas.
            metrics: Diccionario con métricas calculadas.
            strategy_config: Objeto Strategy usado (opcional, para obtener indicadores).
        """
        try:
            from database.models import BacktestRun, Trade, Signal, ExitReason, TradeType, SignalType
            
            # Actualizar BacktestRun con métricas
            backtest_run = db_session.query(BacktestRun).filter(BacktestRun.id == backtest_run_id).first()
            if not backtest_run:
                raise BacktesterError(f"BacktestRun con id {backtest_run_id} no encontrado")
            
            # Importar enum
            from database.models import BacktestStatus as BTStatus
            
            # Actualizar métricas
            backtest_run.status = BTStatus.COMPLETED
            # Convertir valores numpy a tipos nativos de Python para PostgreSQL
            def to_native_type(value):
                """Convierte valores numpy a tipos nativos de Python."""
                if value is None:
                    return None
                if hasattr(value, 'item'):  # numpy types
                    return value.item()
                return float(value) if isinstance(value, (int, float)) else value
            
            backtest_run.total_return = to_native_type(metrics.get('total_return'))
            backtest_run.total_return_pct = to_native_type(metrics.get('total_return_pct'))
            backtest_run.annualized_return = to_native_type(metrics.get('annualized_return'))
            backtest_run.annualized_return_pct = to_native_type(metrics.get('annualized_return_pct'))
            backtest_run.sharpe_ratio = to_native_type(metrics.get('sharpe_ratio'))
            backtest_run.max_drawdown = to_native_type(metrics.get('max_drawdown'))
            backtest_run.max_drawdown_pct = to_native_type(metrics.get('max_drawdown_pct'))
            backtest_run.volatility = to_native_type(metrics.get('volatility'))
            backtest_run.win_rate = to_native_type(metrics.get('win_rate'))
            backtest_run.profit_factor = to_native_type(metrics.get('profit_factor'))
            backtest_run.avg_win = to_native_type(metrics.get('avg_win'))
            backtest_run.avg_loss = to_native_type(metrics.get('avg_loss'))
            # Para enteros, convertir a int nativo
            num_trades = metrics.get('num_trades')
            backtest_run.num_trades = int(num_trades) if num_trades is not None else None
            num_buy_trades = metrics.get('num_buy_trades')
            backtest_run.num_buy_trades = int(num_buy_trades) if num_buy_trades is not None else None
            num_sell_trades = metrics.get('num_sell_trades')
            backtest_run.num_sell_trades = int(num_sell_trades) if num_sell_trades is not None else None
            backtest_run.final_capital = to_native_type(metrics.get('final_value'))
            
            # Fechas del período
            if not results.empty:
                # Convertir índices de pandas a datetime si es necesario
                period_start = results.index[0]
                period_end = results.index[-1]
                if isinstance(period_start, pd.Timestamp):
                    backtest_run.period_start = period_start.to_pydatetime()
                else:
                    backtest_run.period_start = pd.to_datetime(period_start).to_pydatetime()
                
                if isinstance(period_end, pd.Timestamp):
                    backtest_run.period_end = period_end.to_pydatetime()
                else:
                    backtest_run.period_end = pd.to_datetime(period_end).to_pydatetime()
            
            db_session.commit()
            
            # Guardar operaciones
            trades_df = self.get_trades(results)
            for _, trade_row in trades_df.iterrows():
                # Determinar exit_reason basado en cómo se cerró la operación
                # Por ahora, dejamos None ya que no lo rastreamos fácilmente
                exit_reason = None
                
                # Convertir fechas a datetime
                fecha_entrada = trade_row['Fecha Entrada']
                fecha_salida = trade_row['Fecha Salida']
                if isinstance(fecha_entrada, pd.Timestamp):
                    fecha_entrada = fecha_entrada.to_pydatetime()
                else:
                    fecha_entrada = pd.to_datetime(fecha_entrada).to_pydatetime()
                
                if isinstance(fecha_salida, pd.Timestamp):
                    fecha_salida = fecha_salida.to_pydatetime()
                else:
                    fecha_salida = pd.to_datetime(fecha_salida).to_pydatetime()
                
                trade = Trade(
                    backtest_run_id=backtest_run_id,
                    fecha_entrada=fecha_entrada,
                    fecha_salida=fecha_salida,
                    tipo=TradeType.LONG if trade_row['Tipo'] == 'LONG' else TradeType.SHORT,
                    precio_entrada=trade_row['Precio Entrada'],
                    precio_salida=trade_row['Precio Salida'],
                    pnl_dollar=trade_row['P&L ($)'],
                    pnl_percent=trade_row['P&L (%)'],
                    capital_final=trade_row['Capital Final'],
                    exit_reason=exit_reason
                )
                db_session.add(trade)
            
            # Guardar señales (solo BUY y SELL, no HOLD)
            # Obtener detalles de señales si la estrategia los proporciona
            signal_details = {}
            if strategy_config and hasattr(strategy_config, 'get_signal_details'):
                details_list = strategy_config.get_signal_details()
                # Crear mapa por timestamp para acceso rápido
                for detail in details_list:
                    ts = detail.get('timestamp')
                    if ts:
                        signal_details[str(ts)] = detail
            
            for timestamp, signal_value in signals.items():
                # Solo guardar BUY y SELL (no HOLD)
                if signal_value == 0:
                    continue
                    
                # Convertir timestamp a datetime
                if isinstance(timestamp, pd.Timestamp):
                    signal_timestamp = timestamp.to_pydatetime()
                else:
                    signal_timestamp = pd.to_datetime(timestamp).to_pydatetime()
                
                if signal_value == 1:
                    signal_type = SignalType.BUY
                else:
                    signal_type = SignalType.SELL
                
                price = results.loc[timestamp, 'close'] if timestamp in results.index else data.loc[timestamp, 'close']
                
                # Buscar detalles de la señal
                detail = signal_details.get(str(timestamp), {})
                
                # Campos de calidad de señal (nuevos 2026-01-16)
                signal_strength = detail.get('signal_strength')
                value_zone = detail.get('zone')
                signal_reason = detail.get('reason')
                is_absorption = detail.get('is_absorption')
                cvd_momentum = detail.get('cvd_momentum')
                vwap_value = detail.get('vwap')
                
                signal = Signal(
                    backtest_run_id=backtest_run_id,
                    timestamp=signal_timestamp,
                    signal_type=signal_type,
                    price=float(price),
                    rsi_value=None,
                    ma_fast=None,
                    ma_slow=None,
                    trend_sma=None,
                    # Nuevos campos de calidad
                    signal_strength=float(signal_strength) if signal_strength is not None else None,
                    value_zone=str(value_zone) if value_zone else None,
                    signal_reason=str(signal_reason)[:255] if signal_reason else None,
                    is_absorption=bool(is_absorption) if is_absorption is not None else None,
                    cvd_momentum=float(cvd_momentum) if cvd_momentum is not None else None,
                    vwap_value=float(vwap_value) if vwap_value is not None else None,
                    executed=True  # Solo guardamos señales ejecutadas
                )
                db_session.add(signal)
            
            db_session.commit()
            logger.info(f"Backtest {backtest_run_id} guardado en base de datos exitosamente")
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error guardando backtest en BD: {e}")
            raise BacktesterError(f"Error guardando backtest en BD: {e}")
    
    def print_trades(self, trades: pd.DataFrame) -> None:
        """
        Imprime un resumen de las operaciones realizadas.
        
        Args:
            trades: DataFrame con las operaciones.
        """
        if trades.empty:
            print("\nNo se realizaron operaciones durante el período.")
            return
        
        print("\n" + "="*120)
        print("DETALLE DE OPERACIONES")
        print("="*120)
        print(f"{'#':<4} {'Fecha Entrada':<20} {'Fecha Salida':<20} {'Tipo':<6} {'Precio Entrada':>14} {'Precio Salida':>14} {'P&L ($)':>12} {'P&L (%)':>10} {'Capital Final':>14}")
        print("-"*120)
        
        for idx, trade in trades.iterrows():
            tipo_str = trade['Tipo']
            pnl_sign = '+' if trade['P&L ($)'] >= 0 else ''
            pnl_pct_sign = '+' if trade['P&L (%)'] >= 0 else ''
            
            print(f"{idx+1:<4} "
                  f"{str(trade['Fecha Entrada']):<20} "
                  f"{str(trade['Fecha Salida']):<20} "
                  f"{tipo_str:<6} "
                  f"${trade['Precio Entrada']:>13,.2f} "
                  f"${trade['Precio Salida']:>13,.2f} "
                  f"{pnl_sign}${trade['P&L ($)']:>11,.2f} "
                  f"{pnl_pct_sign}{trade['P&L (%)']:>9.2f}% "
                  f"${trade['Capital Final']:>13,.2f}")
        
        print("="*120)
        print(f"\nTotal de operaciones: {len(trades)}")
        print(f"Operaciones largas: {(trades['Tipo'] == 'LONG').sum()}")
        print(f"Operaciones cortas: {(trades['Tipo'] == 'SHORT').sum()}")
        print(f"Operaciones ganadoras: {(trades['P&L ($)'] > 0).sum()}")
        print(f"Operaciones perdedoras: {(trades['P&L ($)'] < 0).sum()}")
        print(f"P&L total: ${trades['P&L ($)'].sum():,.2f}")
        print()
    
    def print_summary(self, metrics: Dict[str, Any]) -> None:
        """
        Imprime un resumen de las métricas en la consola.
        
        Args:
            metrics: Diccionario con las métricas calculadas.
        """
        print("\n" + "="*60)
        print("RESUMEN DEL BACKTEST")
        print("="*60)
        print(f"Capital Inicial:         ${metrics['initial_capital']:,.2f}")
        print(f"Valor Final:             ${metrics['final_value']:,.2f}")
        print(f"\n--- Rendimiento ---")
        print(f"Retorno Total:           {metrics['total_return_pct']:>8.2f}%")
        print(f"Retorno Anualizado:      {metrics['annualized_return_pct']:>8.2f}%")
        print(f"\n--- Riesgo ---")
        print(f"Sharpe Ratio:            {metrics['sharpe_ratio']:>8.2f}")
        print(f"Maximum Drawdown:        {metrics['max_drawdown_pct']:>8.2f}%")
        print(f"Volatilidad Anualizada:  {metrics['volatility']*100:>8.2f}%")
        print(f"\n--- Operaciones ---")
        print(f"Total de Operaciones:    {metrics['num_trades']:>8d}")
        print(f"  - Compras:             {metrics['num_buy_trades']:>8d}")
        print(f"  - Ventas:              {metrics['num_sell_trades']:>8d}")
        print(f"Win Rate:                {metrics['win_rate']*100:>7.2f}%")
        print(f"Profit Factor:           {metrics['profit_factor']:>8.2f}")
        print(f"Promedio Ganancia:       {metrics['avg_win']:>7.2f}%")
        print(f"Promedio Pérdida:        {metrics['avg_loss']:>7.2f}%")
        print("="*60 + "\n")
