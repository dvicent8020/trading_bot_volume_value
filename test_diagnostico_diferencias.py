#!/usr/bin/env python3
"""
Diagnóstico: ¿Por qué los resultados son tan diferentes?
"""

import logging
import pandas as pd
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.volume_value_strategy import VolumeValueStrategy
from trading_bot.backtester import Backtester

logging.basicConfig(level=logging.WARNING)


def analizar_trades(trades: pd.DataFrame) -> dict:
    """Analiza los trades para identificar patrones."""
    if trades.empty:
        return {}
    
    total = len(trades)
    ganadores = len(trades[trades['P&L ($)'] > 0])
    perdedores = len(trades[trades['P&L ($)'] < 0])
    
    longs = trades[trades['Tipo'] == 'LONG']
    shorts = trades[trades['Tipo'] == 'SHORT']
    
    long_winners = len(longs[longs['P&L ($)'] > 0])
    short_winners = len(shorts[shorts['P&L ($)'] > 0])
    
    # Por exit reason
    exit_reasons = trades['Exit Reason'].value_counts().to_dict()
    
    # P&L promedio
    avg_pnl = trades['P&L ($)'].mean()
    avg_win = trades[trades['P&L ($)'] > 0]['P&L ($)'].mean() if ganadores > 0 else 0
    avg_loss = trades[trades['P&L ($)'] < 0]['P&L ($)'].mean() if perdedores > 0 else 0
    
    return {
        'total': total,
        'ganadores': ganadores,
        'perdedores': perdedores,
        'win_rate': ganadores / total * 100 if total > 0 else 0,
        'longs': len(longs),
        'long_winners': long_winners,
        'long_win_rate': long_winners / len(longs) * 100 if len(longs) > 0 else 0,
        'shorts': len(shorts),
        'short_winners': short_winners,
        'short_win_rate': short_winners / len(shorts) * 100 if len(shorts) > 0 else 0,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'exit_reasons': exit_reasons
    }


def main():
    print("\n" + "="*80)
    print("   DIAGNÓSTICO: ¿POR QUÉ LOS RESULTADOS SON DIFERENTES?")
    print("="*80)
    
    # Obtener datos
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data = data_handler.fetch_historical_data(timeframe='1d', days=365)
    
    print(f"\nPeríodo de datos: {data.index[0]} a {data.index[-1]}")
    print(f"Velas: {len(data)}")
    
    # ============================================================
    # TEST 1: Configuración ACTUAL (con absorción mejorada)
    # ============================================================
    print("\n" + "="*80)
    print("TEST 1: Configuración ACTUAL (con absorción mejorada)")
    print("="*80)
    
    strategy_actual = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25,
        disable_longs=False,
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals_actual = strategy_actual.generate_signals(data)
    print(f"Señales: {(signals_actual == 1).sum()} LONG, {(signals_actual == -1).sum()} SHORT")
    
    backtester_actual = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=3.0,
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5
    )
    
    results_actual = backtester_actual.run_backtest(data, signals_actual)
    metrics_actual = backtester_actual.calculate_metrics(results_actual, timeframe='1d')
    trades_actual = backtester_actual.get_trades(results_actual)
    analysis_actual = analizar_trades(trades_actual)
    
    print(f"\nResultados:")
    print(f"  Retorno: {metrics_actual['total_return_pct']:+.2f}%")
    print(f"  Sharpe: {metrics_actual['sharpe_ratio']:.2f}")
    print(f"  Max DD: {metrics_actual['max_drawdown_pct']:.2f}%")
    print(f"\nAnálisis de trades:")
    print(f"  Total: {analysis_actual['total']}")
    print(f"  Win Rate: {analysis_actual['win_rate']:.1f}%")
    print(f"  LONG Win Rate: {analysis_actual['long_win_rate']:.1f}% ({analysis_actual['long_winners']}/{analysis_actual['longs']})")
    print(f"  SHORT Win Rate: {analysis_actual['short_win_rate']:.1f}% ({analysis_actual['short_winners']}/{analysis_actual['shorts']})")
    print(f"  Avg Win: ${analysis_actual['avg_win']:.2f}")
    print(f"  Avg Loss: ${analysis_actual['avg_loss']:.2f}")
    print(f"  Exit Reasons: {analysis_actual['exit_reasons']}")
    
    # ============================================================
    # TEST 2: Sin detector de absorción mejorado (más selectivo)
    # ============================================================
    print("\n" + "="*80)
    print("TEST 2: Config más selectiva (ADX=30, signal_cooldown=10)")
    print("="*80)
    
    strategy_selectivo = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=30,  # Más estricto
        signal_cooldown=10,  # Más tiempo entre señales
        min_signal_strength=0.6,  # Solo señales fuertes
        disable_longs=False,
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals_selectivo = strategy_selectivo.generate_signals(data)
    print(f"Señales: {(signals_selectivo == 1).sum()} LONG, {(signals_selectivo == -1).sum()} SHORT")
    
    backtester_selectivo = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=3.0,
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5
    )
    
    results_selectivo = backtester_selectivo.run_backtest(data, signals_selectivo)
    metrics_selectivo = backtester_selectivo.calculate_metrics(results_selectivo, timeframe='1d')
    trades_selectivo = backtester_selectivo.get_trades(results_selectivo)
    analysis_selectivo = analizar_trades(trades_selectivo)
    
    print(f"\nResultados:")
    print(f"  Retorno: {metrics_selectivo['total_return_pct']:+.2f}%")
    print(f"  Sharpe: {metrics_selectivo['sharpe_ratio']:.2f}")
    print(f"  Max DD: {metrics_selectivo['max_drawdown_pct']:.2f}%")
    if analysis_selectivo:
        print(f"\nAnálisis de trades:")
        print(f"  Total: {analysis_selectivo['total']}")
        print(f"  Win Rate: {analysis_selectivo['win_rate']:.1f}%")
    
    # ============================================================
    # TEST 3: Solo SHORTs (mejor rendimiento histórico)
    # ============================================================
    print("\n" + "="*80)
    print("TEST 3: Solo SHORTs (disable_longs=True)")
    print("="*80)
    
    strategy_shorts = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25,
        disable_longs=True,  # SOLO SHORTS
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals_shorts = strategy_shorts.generate_signals(data)
    print(f"Señales: {(signals_shorts == 1).sum()} LONG, {(signals_shorts == -1).sum()} SHORT")
    
    backtester_shorts = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=3.0,
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5
    )
    
    results_shorts = backtester_shorts.run_backtest(data, signals_shorts)
    metrics_shorts = backtester_shorts.calculate_metrics(results_shorts, timeframe='1d')
    trades_shorts = backtester_shorts.get_trades(results_shorts)
    analysis_shorts = analizar_trades(trades_shorts)
    
    print(f"\nResultados:")
    print(f"  Retorno: {metrics_shorts['total_return_pct']:+.2f}%")
    print(f"  Sharpe: {metrics_shorts['sharpe_ratio']:.2f}")
    print(f"  Max DD: {metrics_shorts['max_drawdown_pct']:.2f}%")
    if analysis_shorts:
        print(f"\nAnálisis de trades:")
        print(f"  Total: {analysis_shorts['total']}")
        print(f"  Win Rate: {analysis_shorts['win_rate']:.1f}%")
    
    # ============================================================
    # RESUMEN COMPARATIVO
    # ============================================================
    print("\n" + "="*80)
    print("RESUMEN COMPARATIVO")
    print("="*80)
    print(f"\n{'Config':<30} {'Retorno':<12} {'Sharpe':<10} {'MaxDD':<12} {'Trades':<8} {'WR':<8}")
    print("-"*80)
    print(f"{'Actual (absorción mejorada)':<30} {metrics_actual['total_return_pct']:>+9.2f}% {metrics_actual['sharpe_ratio']:>9.2f} {metrics_actual['max_drawdown_pct']:>10.2f}% {analysis_actual['total']:>6} {analysis_actual['win_rate']:>6.1f}%")
    print(f"{'Selectivo (ADX=30)':<30} {metrics_selectivo['total_return_pct']:>+9.2f}% {metrics_selectivo['sharpe_ratio']:>9.2f} {metrics_selectivo['max_drawdown_pct']:>10.2f}% {analysis_selectivo.get('total', 0):>6} {analysis_selectivo.get('win_rate', 0):>6.1f}%")
    print(f"{'Solo SHORTs':<30} {metrics_shorts['total_return_pct']:>+9.2f}% {metrics_shorts['sharpe_ratio']:>9.2f} {metrics_shorts['max_drawdown_pct']:>10.2f}% {analysis_shorts.get('total', 0):>6} {analysis_shorts.get('win_rate', 0):>6.1f}%")
    print("-"*80)
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO")
    print("="*80)
    
    if analysis_actual['long_win_rate'] < 40:
        print("\n⚠️ PROBLEMA IDENTIFICADO: LONGs tienen bajo win rate")
        print(f"   Long Win Rate: {analysis_actual['long_win_rate']:.1f}%")
        print("   RECOMENDACIÓN: Considerar disable_longs=True para este período")
    
    if analysis_actual['avg_loss'] < -500:
        print("\n⚠️ PROBLEMA IDENTIFICADO: Pérdidas promedio muy altas")
        print(f"   Avg Loss: ${analysis_actual['avg_loss']:.2f}")
        print("   RECOMENDACIÓN: Reducir stop_loss_pct o leverage")
    
    stop_losses = analysis_actual['exit_reasons'].get('STOP_LOSS', 0)
    if stop_losses / analysis_actual['total'] > 0.5:
        print("\n⚠️ PROBLEMA IDENTIFICADO: Demasiados Stop Loss")
        print(f"   Stop Losses: {stop_losses}/{analysis_actual['total']} ({stop_losses/analysis_actual['total']*100:.1f}%)")
        print("   RECOMENDACIÓN: Ajustar trailing stop o aumentar stop_loss_pct")


if __name__ == "__main__":
    main()
