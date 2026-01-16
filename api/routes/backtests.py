"""
Rutas para gestión de backtests.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database.database import get_db
from database.models import BacktestRun, BacktestStatus, StrategyConfig
from api.schemas import (
    BacktestConfigRequest,
    BacktestRunSchema,
    BacktestRunDetailSchema,
    StrategyConfigSchema,
    StrategyType
)

logger = logging.getLogger(__name__)

router = APIRouter()


def run_backtest_task(config: BacktestConfigRequest, backtest_id: int):
    """Tarea en background para ejecutar backtest."""
    # Crear nueva sesión de BD para la tarea en background
    from database.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Importar aquí para evitar dependencias circulares
        from trading_bot import DataHandler, Backtester, StrategyRegistry
        from trading_bot.exceptions import TradingBotError
        from api.schemas import StrategyType
        
        # Actualizar estado a RUNNING
        backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
        if backtest:
            backtest.status = BacktestStatus.RUNNING
            db.commit()
        
        # Ejecutar backtest
        data_handler = DataHandler(symbol=config.symbol, market_type=config.market_type)
        data = data_handler.fetch_historical_data(
            timeframe=config.timeframe,
            days=config.days
        )
        data_handler.validate_data(data)
        
        # Crear estrategia usando el registro
        strategy_type = config.strategy_type.value if isinstance(config.strategy_type, StrategyType) else config.strategy_type
        
        if strategy_type == StrategyType.SMA_CROSSOVER.value:
            # Configurar estrategia SMA Crossover
            strategy_params = {
                'fast_period': config.fast_period,
                'slow_period': config.slow_period,
                'use_ema': config.use_ema,
                'rsi_period': config.rsi_period,
                'rsi_overbought': config.rsi_overbought,
                'rsi_oversold': config.rsi_oversold,
                'trend_filter_period': config.trend_filter_period,
                'volume_period': config.volume_period,
                'volume_ratio_threshold': config.volume_ratio_threshold,
                'atr_period': config.atr_period,
                'atr_multiplier': config.atr_multiplier,
                'market_regime_enabled': config.market_regime_enabled,
                'adx_period': config.adx_period,
                'adx_threshold': config.adx_threshold,
                'max_volatility_multiplier': config.max_volatility_multiplier
            }
        elif strategy_type == StrategyType.FUNNEL_LOGIC.value:
            # Configurar estrategia Funnel Logic
            strategy_params = {
                'ema_period': config.ema_period or 200,
                'rsi_period': config.rsi_period or 14,
                'rsi_oversold': config.rsi_oversold or 30.0,
                'rsi_overbought': config.rsi_overbought or 70.0,
                'volume_period': config.volume_period or 20,
                'volume_ratio_threshold': config.volume_ratio_threshold or 1.0,
                'delta_confirmation_candles': config.delta_confirmation_candles or 2,
                'delta_lookback': config.delta_lookback or 3
            }
        elif strategy_type == StrategyType.VOLUME_VALUE.value:
            # Configurar estrategia Volume Value Strategy (con filtros ATR y ADX)
            strategy_params = {
                'vwap_period_days': config.vwap_period_days or 7,
                'volume_profile_period': config.volume_profile_period or 7,
                'value_area_percent': config.value_area_percent or 0.68,
                'delta_lookback': config.delta_lookback_vv or 20,  # delta_lookback es el nombre correcto en VolumeValueStrategy
                'volatility_threshold': config.volatility_threshold or 3.0,
                'min_volume_period': config.min_volume_period or 20,
                'lvn_lookback': config.lvn_lookback or 50,
                # Agregar parámetros de filtros ATR y ADX (gestión de riesgo cuantitativa)
                'market_regime_enabled': config.market_regime_enabled if config.market_regime_enabled is not None else True,  # Activado por defecto
                'adx_period': config.adx_period if config.adx_period is not None else 14,
                'adx_threshold': config.adx_threshold if config.adx_threshold is not None else 30.0  # 30.0 por defecto (config conservadora)
            }
        else:
            raise ValueError(f"Tipo de estrategia no soportado: {strategy_type}")
        
        # Filtrar parámetros None
        strategy_params = {k: v for k, v in strategy_params.items() if v is not None}
        
        # Crear instancia de estrategia usando el registro
        strategy = StrategyRegistry.create_strategy(strategy_type, **strategy_params)
        signals = strategy.generate_signals(data)
        
        backtester = Backtester(
            initial_capital=config.initial_capital,
            commission=config.commission,
            stop_loss_pct=config.stop_loss_pct,
            take_profit_pct=config.take_profit_pct,
            market_type=config.market_type,
            leverage=config.leverage,
            trailing_stop_activation=config.trailing_stop_activation,
            trailing_stop_distance=config.trailing_stop_distance,
            volume_reversal_period=config.volume_reversal_period,
            volume_reversal_threshold=config.volume_reversal_threshold,
            atr_period=config.atr_period,
            atr_multiplier=config.atr_multiplier
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=config.timeframe)
        
        # Guardar en base de datos
        backtester.save_to_database(
            db_session=db,
            backtest_run_id=backtest_id,
            results=results,
            data=data,
            signals=signals,
            metrics=metrics,
            strategy_config=strategy
        )
        
    except Exception as e:
        logger.error(f"Error ejecutando backtest {backtest_id}: {e}", exc_info=True)
        backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
        if backtest:
            backtest.status = BacktestStatus.FAILED
            db.commit()
    finally:
        db.close()


@router.post("/run", response_model=BacktestRunSchema)
async def run_backtest(
    config: BacktestConfigRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ejecutar un nuevo backtest.
    
    Crea el registro en la BD y ejecuta el backtest en background.
    """
    # Crear registro de backtest
    backtest_run = BacktestRun(
        name=config.name or f"Backtest {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        status=BacktestStatus.PENDING,
        symbol=config.symbol,
        market_type=config.market_type,
        timeframe=config.timeframe,
        days=config.days,
        initial_capital=config.initial_capital,
        commission=config.commission,
        leverage=config.leverage,
        stop_loss_pct=config.stop_loss_pct,
        take_profit_pct=config.take_profit_pct,
        trailing_stop_activation=config.trailing_stop_activation,
        trailing_stop_distance=config.trailing_stop_distance,
        volume_reversal_period=config.volume_reversal_period,
        volume_reversal_threshold=config.volume_reversal_threshold,
    )
    
    db.add(backtest_run)
    db.commit()
    db.refresh(backtest_run)
    
    # Crear configuración de estrategia
    strategy_type = config.strategy_type.value if isinstance(config.strategy_type, StrategyType) else config.strategy_type
    
    strategy_config = StrategyConfig(
        backtest_run_id=backtest_run.id,
        strategy_type=strategy_type,
        # Parámetros SMA Crossover
        fast_period=config.fast_period if strategy_type == StrategyType.SMA_CROSSOVER.value else None,
        slow_period=config.slow_period if strategy_type == StrategyType.SMA_CROSSOVER.value else None,
        use_ema=config.use_ema if strategy_type == StrategyType.SMA_CROSSOVER.value else None,
        trend_filter_period=config.trend_filter_period if strategy_type == StrategyType.SMA_CROSSOVER.value else None,
        # Parámetros compartidos
        rsi_period=config.rsi_period,
        rsi_overbought=config.rsi_overbought,
        rsi_oversold=config.rsi_oversold,
        volume_period=config.volume_period,
        volume_ratio_threshold=config.volume_ratio_threshold,
        # Filtros críticos (compartidos entre estrategias)
        atr_period=config.atr_period,
        atr_multiplier=config.atr_multiplier,
        market_regime_enabled=config.market_regime_enabled,
        adx_period=config.adx_period,
        adx_threshold=config.adx_threshold,
        max_volatility_multiplier=config.max_volatility_multiplier,
        # Parámetros Funnel Logic
        ema_period=config.ema_period if strategy_type == StrategyType.FUNNEL_LOGIC.value else None,
        delta_confirmation_candles=config.delta_confirmation_candles if strategy_type == StrategyType.FUNNEL_LOGIC.value else None,
        delta_lookback=config.delta_lookback if strategy_type == StrategyType.FUNNEL_LOGIC.value else None,
        # Parámetros Volume Value Strategy
        vwap_period_days=config.vwap_period_days if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        volume_profile_period=config.volume_profile_period if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        value_area_percent=config.value_area_percent if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        delta_lookback_vv=config.delta_lookback_vv if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        volatility_threshold=config.volatility_threshold if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        min_volume_period=config.min_volume_period if strategy_type == StrategyType.VOLUME_VALUE.value else None,
        lvn_lookback=config.lvn_lookback if strategy_type == StrategyType.VOLUME_VALUE.value else None
    )
    
    db.add(strategy_config)
    db.commit()
    
    # Ejecutar backtest en background
    background_tasks.add_task(run_backtest_task, config, backtest_run.id)
    
    return backtest_run


@router.get("/", response_model=List[BacktestRunSchema])
def list_backtests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Listar todos los backtests."""
    backtests = db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).offset(skip).limit(limit).all()
    return backtests


@router.get("/{backtest_id}", response_model=BacktestRunDetailSchema)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    """Obtener detalle de un backtest."""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest no encontrado")
    return backtest


@router.delete("/{backtest_id}")
def delete_backtest(backtest_id: int, db: Session = Depends(get_db)):
    """Eliminar un backtest y sus datos relacionados."""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest no encontrado")
    
    db.delete(backtest)
    db.commit()
    return {"message": "Backtest eliminado exitosamente"}


@router.get("/strategies/available")
def list_available_strategies():
    """
    Lista todas las estrategias disponibles en el sistema.
    
    Returns:
        Diccionario con información de todas las estrategias registradas.
    """
    from trading_bot import StrategyRegistry
    
    strategies = StrategyRegistry.list_strategies()
    return {
        "strategies": strategies,
        "total": len(strategies)
    }
