"""
Modelos SQLAlchemy para la base de datos de trading.
"""

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from .database import Base


class TradeType(str, enum.Enum):
    """Tipo de operación."""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalType(str, enum.Enum):
    """Tipo de señal."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ExitReason(str, enum.Enum):
    """Razón de salida de una operación."""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    SIGNAL = "SIGNAL"


class BacktestStatus(str, enum.Enum):
    """Estado de una ejecución de backtest."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BacktestRun(Base):
    """Modelo para ejecuciones de backtest."""
    
    __tablename__ = "backtest_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(BacktestStatus), default=BacktestStatus.PENDING, nullable=False)
    
    # Parámetros de mercado
    symbol = Column(String(50), nullable=False)
    market_type = Column(String(20), nullable=False)  # 'spot' o 'futures'
    timeframe = Column(String(20), nullable=False)  # '4h', '1d', etc.
    days = Column(Integer, nullable=False)
    
    # Parámetros de capital y comisiones
    initial_capital = Column(Float, nullable=False)
    commission = Column(Float, nullable=False)
    leverage = Column(Float, nullable=False, default=1.0)
    
    # Parámetros de riesgo
    stop_loss_pct = Column(Float, nullable=True)
    take_profit_pct = Column(Float, nullable=True)
    trailing_stop_activation = Column(Float, nullable=True)
    trailing_stop_distance = Column(Float, nullable=True)
    
    # Parámetros de validación de volumen para reversiones
    volume_reversal_period = Column(Integer, nullable=True)
    volume_reversal_threshold = Column(Float, nullable=True)
    
    # Métricas finales
    total_return = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    annualized_return = Column(Float, nullable=True)
    annualized_return_pct = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    num_trades = Column(Integer, nullable=True)
    num_buy_trades = Column(Integer, nullable=True)
    num_sell_trades = Column(Integer, nullable=True)
    
    # Fechas del período analizado
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Capital final
    final_capital = Column(Float, nullable=True)
    
    # Relaciones
    strategy_config = relationship("StrategyConfig", back_populates="backtest_run", uselist=False, cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="backtest_run", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="backtest_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_backtest_runs_created_at', 'created_at'),
        Index('idx_backtest_runs_status', 'status'),
    )


class StrategyConfig(Base):
    """Modelo para configuración de estrategia."""
    
    __tablename__ = "strategy_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Tipo de estrategia
    strategy_type = Column(String(50), nullable=False, default="SMA_CROSSOVER", index=True)
    
    # Parámetros de medias móviles (SMA Crossover)
    fast_period = Column(Integer, nullable=True)
    slow_period = Column(Integer, nullable=True)
    use_ema = Column(Boolean, nullable=True)
    
    # Filtro de tendencia (SMA Crossover)
    trend_filter_period = Column(Integer, nullable=True)
    
    # Parámetros RSI (compartidos)
    rsi_period = Column(Integer, nullable=True)
    rsi_overbought = Column(Float, nullable=True)
    rsi_oversold = Column(Float, nullable=True)
    
    # Filtro de volumen (compartido)
    volume_period = Column(Integer, nullable=True)
    volume_ratio_threshold = Column(Float, nullable=True)
    
    # Filtros críticos (ATR y Market Regime)
    atr_period = Column(Integer, nullable=True)
    atr_multiplier = Column(Float, nullable=True)
    market_regime_enabled = Column(Boolean, nullable=True)
    adx_period = Column(Integer, nullable=True)
    adx_threshold = Column(Float, nullable=True)
    max_volatility_multiplier = Column(Float, nullable=True)
    
    # Parámetros específicos de Funnel Logic
    ema_period = Column(Integer, nullable=True)  # EMA para contexto
    delta_confirmation_candles = Column(Integer, nullable=True)  # Velas de confirmación
    delta_lookback = Column(Integer, nullable=True)  # Lookback para Delta
    
    # Parámetros específicos de Volume Value Strategy
    vwap_period_days = Column(Integer, nullable=True)  # Período VWAP en días
    volume_profile_period = Column(Integer, nullable=True)  # Período para Volume Profile
    value_area_percent = Column(Float, nullable=True)  # Porcentaje Value Area (0.68 = 68%)
    delta_lookback_vv = Column(Integer, nullable=True)  # Lookback para CVD
    volatility_threshold = Column(Float, nullable=True)  # Threshold volatilidad climática
    min_volume_period = Column(Integer, nullable=True)  # Período mínimo para volumen
    lvn_lookback = Column(Integer, nullable=True)  # Lookback para LVN
    
    # Relación
    backtest_run = relationship("BacktestRun", back_populates="strategy_config")


class Trade(Base):
    """Modelo para operaciones individuales."""
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    
    fecha_entrada = Column(DateTime(timezone=True), nullable=False)
    fecha_salida = Column(DateTime(timezone=True), nullable=False)
    tipo = Column(Enum(TradeType), nullable=False)
    
    precio_entrada = Column(Float, nullable=False)
    precio_salida = Column(Float, nullable=False)
    
    pnl_dollar = Column(Float, nullable=False)
    pnl_percent = Column(Float, nullable=False)
    
    capital_final = Column(Float, nullable=False)
    
    exit_reason = Column(Enum(ExitReason), nullable=True)
    
    # Campo para stop loss (especialmente útil para VolumeValueStrategy con LVN)
    stop_loss_price = Column(Float, nullable=True)
    
    # Relación
    backtest_run = relationship("BacktestRun", back_populates="trades")
    
    __table_args__ = (
        Index('idx_trades_backtest_run_id', 'backtest_run_id'),
        Index('idx_trades_fecha_entrada', 'fecha_entrada'),
        Index('idx_trades_tipo', 'tipo'),
    )


class Signal(Base):
    """Modelo para señales generadas."""
    
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False)
    signal_type = Column(Enum(SignalType), nullable=False)
    
    price = Column(Float, nullable=False)
    
    # Valores de indicadores en el momento de la señal
    rsi_value = Column(Float, nullable=True)
    ma_fast = Column(Float, nullable=True)
    ma_slow = Column(Float, nullable=True)
    trend_sma = Column(Float, nullable=True)
    
    # Campos específicos para VolumeValueStrategy
    vwap_value = Column(Float, nullable=True)
    vpoc_level = Column(Float, nullable=True)
    delta_divergence_detected = Column(Boolean, nullable=True)
    
    executed = Column(Boolean, default=False, nullable=False)  # Si la señal resultó en una operación
    
    # Relación
    backtest_run = relationship("BacktestRun", back_populates="signals")
    
    __table_args__ = (
        Index('idx_signals_backtest_run_id', 'backtest_run_id'),
        Index('idx_signals_timestamp', 'timestamp'),
        Index('idx_signals_signal_type', 'signal_type'),
    )


class MarketData(Base):
    """Modelo para datos de mercado OHLCV (opcional, para análisis avanzado)."""
    
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    symbol = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    __table_args__ = (
        Index('idx_market_data_symbol_timeframe', 'symbol', 'timeframe'),
        Index('idx_market_data_timestamp', 'timestamp'),
        Index('idx_market_data_symbol_timestamp', 'symbol', 'timestamp'),
    )
