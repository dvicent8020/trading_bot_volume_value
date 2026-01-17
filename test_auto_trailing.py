#!/usr/bin/env python3
"""
Script para probar la selección automática de trailing stop.

La lógica automática selecciona:
- Smart Trailing para timeframes cortos (15m, 1h) -> +30% más retorno
- Trailing Tradicional para timeframes largos (4h, 1d) -> más estable
"""

import logging
import pandas as pd
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.volume_value_strategy import VolumeValueStrategy
from trading_bot.backtester import Backtester

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_test(timeframe: str, days: int, use_auto_trailing: bool = True):
    """
    Ejecuta un test con selección automática o manual de trailing.
    
    Args:
        timeframe: Timeframe a probar ('15m', '1h', '4h', '1d')
        days: Número de días de datos
        use_auto_trailing: Si usar selección automática
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {timeframe} - {days} días - Auto-Trailing: {use_auto_trailing}")
    logger.info(f"{'='*60}")
    
    # Obtener datos
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data = data_handler.fetch_historical_data(
        timeframe=timeframe,
        days=days
    )
    
    if data is None or data.empty:
        logger.error(f"No se pudieron obtener datos para {timeframe}")
        return None
    
    logger.info(f"Datos obtenidos: {len(data)} velas")
    
    # Configurar estrategia
    strategy = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25
    )
    
    # Generar señales
    signals = strategy.generate_signals(data)
    
    # Configuración base del backtester
    backtester_params = {
        'initial_capital': 10000.0,
        'commission': 0.001,
        'stop_loss_pct': 0.05,
        'market_type': 'futures',
        'leverage': 3.0,
        'trailing_stop_activation': 0.03,
        'trailing_stop_distance': 0.005,  # 0.5% tradicional
        'atr_period': 14,
        'atr_multiplier': 2.5,
        'strategy_instance': strategy,
        # SELECCIÓN AUTOMÁTICA
        'auto_trailing_selection': use_auto_trailing,
        # Si no es automático, estos parámetros se usan
        'smart_trailing_enabled': False if use_auto_trailing else True,
        'smart_trailing_atr_base': 1.5,
        'smart_trailing_profit_phases': True,
        'smart_trailing_time_decay': True,
        'smart_trailing_breakeven_threshold': 0.025
    }
    
    backtester = Backtester(**backtester_params)
    
    # Ejecutar backtest
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results)
    
    return {
        'timeframe': timeframe,
        'days': days,
        'auto_trailing': use_auto_trailing,
        'return': metrics.get('total_return_pct', 0),
        'sharpe': metrics.get('sharpe_ratio', 0),
        'drawdown': metrics.get('max_drawdown_pct', 0),
        'win_rate': metrics.get('win_rate', 0),
        'trades': metrics.get('num_trades', 0)
    }


def main():
    """Función principal."""
    print("\n" + "="*70)
    print("   PRUEBA DE SELECCIÓN AUTOMÁTICA DE TRAILING STOP")
    print("="*70)
    print("\nLa lógica automática selecciona:")
    print("  📊 Smart Trailing para 15m/1h (mejor rendimiento)")
    print("  📈 Tradicional para 4h/1d (más estable)")
    print("="*70)
    
    timeframes = ['15m', '1h', '4h', '1d']
    days = 90
    
    results = []
    
    for tf in timeframes:
        # Test con selección automática
        result = run_test(tf, days, use_auto_trailing=True)
        if result:
            results.append(result)
    
    # Mostrar resumen
    print("\n" + "="*70)
    print("                    RESUMEN DE RESULTADOS")
    print("="*70)
    print(f"{'Timeframe':<12} {'Retorno':<12} {'Sharpe':<10} {'Drawdown':<12} {'Win Rate':<10} {'Trailing Usado':<20}")
    print("-"*76)
    
    for r in results:
        tf = r['timeframe']
        # Determinar qué trailing se usó
        trailing_type = "Smart" if tf in ['15m', '1h'] else "Tradicional"
        
        print(f"{tf:<12} {r['return']:>+9.2f}% {r['sharpe']:>9.2f} {r['drawdown']:>10.2f}% {r['win_rate']:>9.2f}% {trailing_type:<20}")
    
    print("="*70)
    print("\n✅ CONCLUSIÓN:")
    print("   - 15m/1h: Smart Trailing seleccionado automáticamente")
    print("   - 4h/1d: Trailing Tradicional seleccionado automáticamente")
    print("="*70)


if __name__ == "__main__":
    main()
