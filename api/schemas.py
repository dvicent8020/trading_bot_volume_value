"""
Schemas Pydantic para request/response de la API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TradeType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    SIGNAL = "SIGNAL"


class BacktestStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyType(str, Enum):
    """Tipos de estrategias disponibles."""
    SMA_CROSSOVER = "SMA_CROSSOVER"
    FUNNEL_LOGIC = "FUNNEL_LOGIC"
    VOLUME_VALUE = "VOLUME_VALUE"


# ==================== Request Schemas ====================

class BacktestConfigRequest(BaseModel):
    """Schema para configuración de backtest."""
    name: Optional[str] = None
    symbol: str = "BTC/USDT"
    market_type: str = "futures"
    timeframe: str = "4h"
    days: int = 365
    initial_capital: float = 5000.0
    commission: float = 0.001
    leverage: float = 10.0
    
    # Tipo de estrategia
    strategy_type: StrategyType = StrategyType.SMA_CROSSOVER
    
    # Parámetros de riesgo
    stop_loss_pct: Optional[float] = 0.015
    take_profit_pct: Optional[float] = 0.08
    trailing_stop_activation: Optional[float] = 0.05
    trailing_stop_distance: Optional[float] = 0.02
    atr_period: Optional[int] = None
    atr_multiplier: Optional[float] = None
    
    # Parámetros de estrategia SMA Crossover
    fast_period: int = 15
    slow_period: int = 40
    use_ema: bool = False
    trend_filter_period: Optional[int] = 100
    
    # Parámetros RSI (compartidos)
    rsi_period: Optional[int] = 14
    rsi_overbought: Optional[float] = 75.0
    rsi_oversold: Optional[float] = 25.0
    
    # Parámetros de volumen (compartidos)
    volume_period: Optional[int] = None
    volume_ratio_threshold: Optional[float] = None
    
    # Parámetros de validación de volumen para reversiones
    volume_reversal_period: Optional[int] = None
    volume_reversal_threshold: Optional[float] = None
    
    # Parámetros de filtros críticos (ATR y Regímenes de Mercado)
    market_regime_enabled: bool = False
    adx_period: int = 14
    adx_threshold: float = 25.0
    max_volatility_multiplier: Optional[float] = None
    
    # Nuevos parámetros optimizados (2026-01-16)
    adx_slope_enabled: bool = True  # ⚠️ CRÍTICO para rentabilidad
    use_normalized_cvd: bool = True  # CVD normalizado
    signal_cooldown: int = 5  # Velas entre señales
    
    # Parámetros específicos de Funnel Logic
    ema_period: Optional[int] = 200  # Para Funnel Logic
    delta_confirmation_candles: Optional[int] = 2  # Para Funnel Logic
    delta_lookback: Optional[int] = 3  # Para Funnel Logic
    
    # Parámetros específicos de Volume Value Strategy
    vwap_period_days: Optional[int] = 7  # Para Volume Value Strategy
    volume_profile_period: Optional[int] = 7  # Para Volume Value Strategy
    value_area_percent: Optional[float] = 0.68  # Para Volume Value Strategy (68%)
    delta_lookback_vv: Optional[int] = 20  # Para Volume Value Strategy (CVD)
    volatility_threshold: Optional[float] = 3.0  # Para Volume Value Strategy (300%)
    min_volume_period: Optional[int] = 20  # Para Volume Value Strategy
    lvn_lookback: Optional[int] = 50  # Para Volume Value Strategy


# ==================== Response Schemas ====================

class StrategyConfigSchema(BaseModel):
    """Schema para configuración de estrategia."""
    id: int
    backtest_run_id: int
    strategy_type: str = "SMA_CROSSOVER"
    
    # Parámetros SMA Crossover
    fast_period: Optional[int] = None
    slow_period: Optional[int] = None
    use_ema: Optional[bool] = None
    trend_filter_period: Optional[int] = None
    
    # Parámetros compartidos (RSI, Volumen)
    rsi_period: Optional[int] = None
    rsi_overbought: Optional[float] = None
    rsi_oversold: Optional[float] = None
    volume_period: Optional[int] = None
    volume_ratio_threshold: Optional[float] = None
    
    # Parámetros filtros críticos
    atr_period: Optional[int] = None
    atr_multiplier: Optional[float] = None
    market_regime_enabled: Optional[bool] = False
    adx_period: Optional[int] = None
    adx_threshold: Optional[float] = None
    max_volatility_multiplier: Optional[float] = None
    
    # Parámetros específicos Funnel Logic
    ema_period: Optional[int] = None
    delta_confirmation_candles: Optional[int] = None
    delta_lookback: Optional[int] = None
    
    # Parámetros específicos Volume Value Strategy
    vwap_period_days: Optional[int] = None
    volume_profile_period: Optional[int] = None
    value_area_percent: Optional[float] = None
    delta_lookback_vv: Optional[int] = None
    volatility_threshold: Optional[float] = None
    min_volume_period: Optional[int] = None
    lvn_lookback: Optional[int] = None
    
    class Config:
        from_attributes = True


class TradeSchema(BaseModel):
    """Schema para operación individual."""
    id: int
    backtest_run_id: int
    fecha_entrada: datetime
    fecha_salida: datetime
    tipo: TradeType
    precio_entrada: float
    precio_salida: float
    pnl_dollar: float
    pnl_percent: float
    capital_final: float
    exit_reason: Optional[ExitReason] = None
    stop_loss_price: Optional[float] = None
    
    class Config:
        from_attributes = True


class SignalSchema(BaseModel):
    """Schema para señal generada."""
    id: int
    backtest_run_id: int
    timestamp: datetime
    signal_type: SignalType
    price: float
    rsi_value: Optional[float] = None
    ma_fast: Optional[float] = None
    ma_slow: Optional[float] = None
    trend_sma: Optional[float] = None
    vwap_value: Optional[float] = None
    vpoc_level: Optional[float] = None
    delta_divergence_detected: Optional[bool] = None
    # Nuevos campos de calidad de señal (2026-01-16)
    signal_strength: Optional[float] = None  # Score 0.0-1.0
    value_zone: Optional[str] = None  # VPOC, VAH, VAL, VALUE_AREA, EXTREMO
    signal_reason: Optional[str] = None  # Razón de la señal
    is_absorption: Optional[bool] = None  # Si es señal de absorción
    cvd_momentum: Optional[float] = None  # Momentum del CVD
    executed: bool
    
    class Config:
        from_attributes = True


class MetricsSchema(BaseModel):
    """Schema para métricas de rendimiento."""
    total_return: Optional[float] = None
    total_return_pct: Optional[float] = None
    annualized_return: Optional[float] = None
    annualized_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    volatility: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    num_trades: Optional[int] = None
    num_buy_trades: Optional[int] = None
    num_sell_trades: Optional[int] = None


class BacktestRunSchema(BaseModel):
    """Schema para ejecución de backtest."""
    id: int
    name: Optional[str] = None
    created_at: datetime
    status: BacktestStatus
    symbol: str
    market_type: str
    timeframe: str
    days: int
    initial_capital: float
    commission: float
    leverage: float
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_activation: Optional[float] = None
    trailing_stop_distance: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    final_capital: Optional[float] = None
    
    # Métricas (usando MetricsSchema)
    total_return: Optional[float] = None
    total_return_pct: Optional[float] = None
    annualized_return: Optional[float] = None
    annualized_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    volatility: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    num_trades: Optional[int] = None
    num_buy_trades: Optional[int] = None
    num_sell_trades: Optional[int] = None
    
    class Config:
        from_attributes = True


class BacktestRunDetailSchema(BacktestRunSchema):
    """Schema para detalle completo de backtest (incluye relaciones)."""
    strategy_config: Optional[StrategyConfigSchema] = None
    trades: List[TradeSchema] = []
    signals: List[SignalSchema] = []


class TradeStatsSchema(BaseModel):
    """Schema para estadísticas agregadas de operaciones."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    largest_win: float
    largest_loss: float
