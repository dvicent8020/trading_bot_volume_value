#!/usr/bin/env python3
"""
Script para verificar que los cálculos de métricas son correctos
y comparar con resultados anteriores.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.volume_value_strategy import VolumeValueStrategy
from trading_bot.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_drawdown_calculation():
    """Verifica que el cálculo del drawdown es correcto."""
    print("\n" + "="*70)
    print("VERIFICACIÓN 1: Cálculo del Drawdown")
    print("="*70)
    
    # Crear datos de prueba conocidos
    # Capital inicial: 10000
    # Secuencia: 10000 -> 12000 -> 11000 -> 13000 -> 10000
    # Drawdown esperado: (10000 - 13000) / 13000 = -23.08%
    
    test_capital = [10000, 12000, 11000, 13000, 10000]
    initial = 10000
    
    # Calcular cumulative returns
    cumulative_returns = [(c - initial) / initial for c in test_capital]
    print(f"\nCapital: {test_capital}")
    print(f"Cumulative Returns: {[f'{r:.4f}' for r in cumulative_returns]}")
    
    # Calcular drawdown
    running_max = []
    max_so_far = cumulative_returns[0]
    for r in cumulative_returns:
        max_so_far = max(max_so_far, r)
        running_max.append(max_so_far)
    
    drawdown = [cr - rm for cr, rm in zip(cumulative_returns, running_max)]
    max_drawdown = min(drawdown)
    
    print(f"Running Max: {[f'{r:.4f}' for r in running_max]}")
    print(f"Drawdown: {[f'{d:.4f}' for d in drawdown]}")
    print(f"Max Drawdown: {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
    
    # Verificación manual
    # En el punto 5 (capital=10000): cumulative_return = 0%
    # Running max en ese punto = 30% (cuando capital fue 13000)
    # Drawdown = 0% - 30% = -30%
    expected_dd = (10000 - 13000) / 13000  # -23.08% desde el pico
    # Pero usando cumulative returns desde initial:
    # cumulative en pico (13000) = 0.30
    # cumulative en valle (10000) = 0.00
    # drawdown = 0.00 - 0.30 = -0.30 = -30%
    
    print(f"\nVerificación:")
    print(f"  - Pico: ${13000} (cum_ret = {(13000-10000)/10000:.2%})")
    print(f"  - Valle: ${10000} (cum_ret = {(10000-10000)/10000:.2%})")
    print(f"  - Drawdown calculado: {max_drawdown:.2%}")
    print(f"  - Drawdown esperado: -30.00%")
    
    if abs(max_drawdown - (-0.30)) < 0.01:
        print("  ✅ Cálculo CORRECTO")
    else:
        print("  ❌ Cálculo INCORRECTO")
    
    return abs(max_drawdown - (-0.30)) < 0.01


def test_volume_value_optimal_config():
    """Prueba Volume Value con la configuración óptima documentada."""
    print("\n" + "="*70)
    print("VERIFICACIÓN 2: Volume Value con Config Óptima (1D, 365d)")
    print("="*70)
    
    # Obtener datos
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data = data_handler.fetch_historical_data(timeframe='1d', days=365)
    
    print(f"\nDatos: {len(data)} velas")
    print(f"Período: {data.index[0]} a {data.index[-1]}")
    
    # Configuración ÓPTIMA documentada (del RESULTADOS_VOLUME_VALUE_STRATEGY.md)
    print("\nConfiguración ÓPTIMA:")
    print("  - Leverage: 3.0x")
    print("  - Stop Loss: 5%")
    print("  - Trailing Activation: 3%")
    print("  - Trailing Distance: 1%")
    print("  - Take Profit: 12%")
    print("  - ADX Threshold: 25")
    print("  - disable_longs: False")
    print("  - require_uptrend_for_longs: True")
    
    strategy = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25,
        disable_longs=False,  # IMPORTANTE: No deshabilitar LONGs en 1D
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals = strategy.generate_signals(data)
    long_signals = (signals == 1).sum()
    short_signals = (signals == -1).sum()
    print(f"\nSeñales: {long_signals} LONG, {short_signals} SHORT")
    
    # Backtester con config óptima
    backtester = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=3.0,
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5,
        strategy_instance=strategy,
        auto_trailing_selection=False,  # Usar trailing tradicional para 1D
        smart_trailing_enabled=False
    )
    
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, timeframe='1d')
    
    print(f"\nRESULTADOS:")
    print(f"  - Retorno: {metrics['total_return_pct']:+.2f}%")
    print(f"  - Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"  - Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  - Win Rate: {metrics['win_rate']:.2f}%")
    print(f"  - Trades: {metrics['num_trades']}")
    
    print(f"\nCOMPARACIÓN con resultados documentados:")
    print(f"  Documentado: +91.65%, Sharpe 2.01, DD -28%")
    print(f"  Actual:      {metrics['total_return_pct']:+.2f}%, Sharpe {metrics['sharpe_ratio']:.2f}, DD {metrics['max_drawdown_pct']:.2f}%")
    
    # Verificar trades individualmente
    trades = backtester.get_trades(results)
    if len(trades) > 0:
        print(f"\nDETALLE DE TRADES:")
        print(trades[['Entry Date', 'Exit Date', 'Type', 'Entry Price', 'Exit Price', 'P&L ($)', 'P&L (%)', 'Exit Reason']].to_string())
    
    return metrics


def test_volume_value_4h_shorts_only():
    """Prueba Volume Value 4H solo SHORTs."""
    print("\n" + "="*70)
    print("VERIFICACIÓN 3: Volume Value 4H Solo SHORTs (90d)")
    print("="*70)
    
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data = data_handler.fetch_historical_data(timeframe='4h', days=90)
    
    print(f"\nDatos: {len(data)} velas")
    
    strategy = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25,
        disable_longs=True,  # Solo SHORTs
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals = strategy.generate_signals(data)
    long_signals = (signals == 1).sum()
    short_signals = (signals == -1).sum()
    print(f"\nSeñales: {long_signals} LONG, {short_signals} SHORT")
    
    # Config óptima para 4H SHORTs: 10x leverage
    backtester = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=10.0,  # 10x para 4H SHORTs
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5,
        strategy_instance=strategy,
        auto_trailing_selection=False,
        smart_trailing_enabled=False
    )
    
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, timeframe='4h')
    
    print(f"\nRESULTADOS:")
    print(f"  - Retorno: {metrics['total_return_pct']:+.2f}%")
    print(f"  - Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"  - Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  - Win Rate: {metrics['win_rate']:.2f}%")
    
    print(f"\nCOMPARACIÓN con resultados documentados:")
    print(f"  Documentado: +79.55%, Sharpe 3.40, DD -22%, WR 100%")
    print(f"  Actual:      {metrics['total_return_pct']:+.2f}%, Sharpe {metrics['sharpe_ratio']:.2f}, DD {metrics['max_drawdown_pct']:.2f}%, WR {metrics['win_rate']:.2f}%")
    
    return metrics


def main():
    print("\n" + "="*70)
    print("   VERIFICACIÓN DE CÁLCULOS Y CONFIGURACIONES")
    print("="*70)
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Test 1: Verificar fórmula de drawdown
    dd_ok = verify_drawdown_calculation()
    
    # Test 2: Volume Value 1D config óptima
    metrics_1d = test_volume_value_optimal_config()
    
    # Test 3: Volume Value 4H solo SHORTs
    metrics_4h = test_volume_value_4h_shorts_only()
    
    print("\n" + "="*70)
    print("   RESUMEN DE VERIFICACIÓN")
    print("="*70)
    print(f"\n1. Cálculo Drawdown: {'✅ CORRECTO' if dd_ok else '❌ INCORRECTO'}")
    print(f"\n2. Volume Value 1D 365d:")
    print(f"   - Documentado: +91.65%, DD -28%")
    print(f"   - Actual: {metrics_1d['total_return_pct']:+.2f}%, DD {metrics_1d['max_drawdown_pct']:.2f}%")
    if abs(metrics_1d['total_return_pct'] - 91.65) > 20:
        print(f"   ⚠️ DIFERENCIA SIGNIFICATIVA - Posibles causas:")
        print(f"      - Datos diferentes (período distinto)")
        print(f"      - Cambios en la estrategia")
        print(f"      - Configuración diferente")
    
    print(f"\n3. Volume Value 4H 90d (Solo SHORTs):")
    print(f"   - Documentado: +79.55%, DD -22%")
    print(f"   - Actual: {metrics_4h['total_return_pct']:+.2f}%, DD {metrics_4h['max_drawdown_pct']:.2f}%")


if __name__ == "__main__":
    main()
