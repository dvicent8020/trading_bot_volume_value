#!/usr/bin/env python3
"""
Script de comparación: Funnel Logic vs Volume Value Strategy
Ejecuta pruebas completas en múltiples timeframes y períodos.
"""

import logging
import pandas as pd
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.funnel_strategy import FunnelStrategy
from trading_bot.volume_value_strategy import VolumeValueStrategy
from trading_bot.backtester import Backtester

# Configurar logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_funnel_test(data: pd.DataFrame, timeframe: str, leverage: float = 10.0) -> dict:
    """Ejecuta test con Funnel Logic Strategy."""
    # Ajustar EMA según datos disponibles
    ema_period = min(200, len(data) - 20) if len(data) < 220 else 200
    
    strategy = FunnelStrategy(
        ema_period=ema_period,
        rsi_period=14,
        rsi_oversold=30.0,
        rsi_overbought=70.0,
        volume_period=20,
        volume_ratio_threshold=1.0,
        delta_confirmation_candles=2,
        delta_lookback=3
    )
    
    signals = strategy.generate_signals(data)
    
    backtester = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=None,
        take_profit_pct=0.08,
        market_type='futures',
        leverage=leverage,
        trailing_stop_activation=0.05,
        trailing_stop_distance=0.02,
        atr_period=14,
        atr_multiplier=2.0
    )
    
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, timeframe=timeframe)
    
    return {
        'strategy': 'Funnel Logic',
        'signals': (signals != 0).sum(),
        'long_signals': (signals == 1).sum(),
        'short_signals': (signals == -1).sum(),
        'return': metrics.get('total_return_pct', 0),
        'sharpe': metrics.get('sharpe_ratio', 0),
        'drawdown': metrics.get('max_drawdown_pct', 0),
        'win_rate': metrics.get('win_rate', 0),
        'trades': metrics.get('num_trades', 0)
    }


def run_volume_value_test(data: pd.DataFrame, timeframe: str, leverage: float = 3.0) -> dict:
    """Ejecuta test con Volume Value Strategy."""
    strategy = VolumeValueStrategy(
        vwap_period_days=5,
        volume_profile_period=7,
        market_regime_enabled=True,
        adx_period=14,
        adx_threshold=25,
        disable_longs=timeframe == '4h',  # Deshabilitar LONGs en 4H
        require_uptrend_for_longs=True,
        trend_filter_period=50
    )
    
    signals = strategy.generate_signals(data)
    
    backtester = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.12,
        market_type='futures',
        leverage=leverage,
        trailing_stop_activation=0.03,
        trailing_stop_distance=0.01,
        atr_period=14,
        atr_multiplier=2.5,
        strategy_instance=strategy,
        auto_trailing_selection=True
    )
    
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, timeframe=timeframe)
    
    return {
        'strategy': 'Volume Value',
        'signals': (signals != 0).sum(),
        'long_signals': (signals == 1).sum(),
        'short_signals': (signals == -1).sum(),
        'return': metrics.get('total_return_pct', 0),
        'sharpe': metrics.get('sharpe_ratio', 0),
        'drawdown': metrics.get('max_drawdown_pct', 0),
        'win_rate': metrics.get('win_rate', 0),
        'trades': metrics.get('num_trades', 0)
    }


def main():
    """Función principal."""
    print("\n" + "="*80)
    print("   COMPARACIÓN: FUNNEL LOGIC vs VOLUME VALUE STRATEGY")
    print("="*80)
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*80)
    
    # Configuraciones a probar
    tests = [
        {'timeframe': '15m', 'days': 90, 'funnel_lev': 10.0, 'vv_lev': 3.0},
        {'timeframe': '1h', 'days': 90, 'funnel_lev': 10.0, 'vv_lev': 3.0},
        {'timeframe': '4h', 'days': 90, 'funnel_lev': 10.0, 'vv_lev': 3.0},
        {'timeframe': '4h', 'days': 365, 'funnel_lev': 10.0, 'vv_lev': 3.0},
        {'timeframe': '1d', 'days': 90, 'funnel_lev': 10.0, 'vv_lev': 3.0},
        {'timeframe': '1d', 'days': 365, 'funnel_lev': 10.0, 'vv_lev': 3.0},
    ]
    
    all_results = []
    
    for test in tests:
        tf = test['timeframe']
        days = test['days']
        
        print(f"\n{'─'*80}")
        print(f"  TEST: {tf} - {days} días")
        print(f"{'─'*80}")
        
        # Obtener datos
        data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
        data = data_handler.fetch_historical_data(timeframe=tf, days=days)
        
        if data is None or data.empty:
            print(f"  ❌ Error obteniendo datos para {tf}")
            continue
        
        print(f"  📊 Datos: {len(data)} velas")
        
        # Ejecutar Funnel Logic
        print(f"  ⏳ Ejecutando Funnel Logic (Leverage {test['funnel_lev']}x)...")
        try:
            funnel_result = run_funnel_test(data, tf, test['funnel_lev'])
            funnel_result['timeframe'] = tf
            funnel_result['days'] = days
            all_results.append(funnel_result)
            print(f"     ✅ Retorno: {funnel_result['return']:+.2f}%, Sharpe: {funnel_result['sharpe']:.2f}, DD: {funnel_result['drawdown']:.2f}%")
        except Exception as e:
            print(f"     ❌ Error: {e}")
        
        # Ejecutar Volume Value
        print(f"  ⏳ Ejecutando Volume Value (Leverage {test['vv_lev']}x)...")
        try:
            vv_result = run_volume_value_test(data, tf, test['vv_lev'])
            vv_result['timeframe'] = tf
            vv_result['days'] = days
            all_results.append(vv_result)
            print(f"     ✅ Retorno: {vv_result['return']:+.2f}%, Sharpe: {vv_result['sharpe']:.2f}, DD: {vv_result['drawdown']:.2f}%")
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    # Resumen comparativo
    print("\n" + "="*80)
    print("                      RESUMEN COMPARATIVO")
    print("="*80)
    
    # Agrupar por timeframe/days
    print(f"\n{'TF':<6} {'Días':<6} {'Estrategia':<15} {'Retorno':<12} {'Sharpe':<8} {'DD':<10} {'WR':<8} {'Trades':<8}")
    print("─"*80)
    
    for i in range(0, len(all_results), 2):
        if i+1 < len(all_results):
            r1 = all_results[i]
            r2 = all_results[i+1]
            
            print(f"{r1['timeframe']:<6} {r1['days']:<6} {r1['strategy']:<15} {r1['return']:>+9.2f}% {r1['sharpe']:>7.2f} {r1['drawdown']:>8.2f}% {r1['win_rate']:>6.1f}% {r1['trades']:>6}")
            print(f"{'':6} {'':6} {r2['strategy']:<15} {r2['return']:>+9.2f}% {r2['sharpe']:>7.2f} {r2['drawdown']:>8.2f}% {r2['win_rate']:>6.1f}% {r2['trades']:>6}")
            
            # Indicar ganador
            if r1['return'] > r2['return']:
                winner = r1['strategy']
            else:
                winner = r2['strategy']
            print(f"{'':6} {'':6} {'🏆 Mejor:':<15} {winner}")
            print("─"*80)
    
    # Estadísticas globales
    funnel_results = [r for r in all_results if r['strategy'] == 'Funnel Logic']
    vv_results = [r for r in all_results if r['strategy'] == 'Volume Value']
    
    if funnel_results and vv_results:
        print("\n" + "="*80)
        print("                    ESTADÍSTICAS GLOBALES")
        print("="*80)
        
        funnel_avg_return = sum(r['return'] for r in funnel_results) / len(funnel_results)
        vv_avg_return = sum(r['return'] for r in vv_results) / len(vv_results)
        
        funnel_avg_sharpe = sum(r['sharpe'] for r in funnel_results) / len(funnel_results)
        vv_avg_sharpe = sum(r['sharpe'] for r in vv_results) / len(vv_results)
        
        funnel_avg_dd = sum(r['drawdown'] for r in funnel_results) / len(funnel_results)
        vv_avg_dd = sum(r['drawdown'] for r in vv_results) / len(vv_results)
        
        funnel_wins = sum(1 for f, v in zip(funnel_results, vv_results) if f['return'] > v['return'])
        vv_wins = len(funnel_results) - funnel_wins
        
        print(f"\n{'Métrica':<25} {'Funnel Logic':<20} {'Volume Value':<20}")
        print("─"*65)
        print(f"{'Retorno Promedio':<25} {funnel_avg_return:>+17.2f}% {vv_avg_return:>+17.2f}%")
        print(f"{'Sharpe Promedio':<25} {funnel_avg_sharpe:>18.2f} {vv_avg_sharpe:>18.2f}")
        print(f"{'Drawdown Promedio':<25} {funnel_avg_dd:>17.2f}% {vv_avg_dd:>17.2f}%")
        print(f"{'Victorias':<25} {funnel_wins:>18} {vv_wins:>18}")
        
        print("\n" + "="*80)
        if funnel_avg_return > vv_avg_return:
            print("   🏆 GANADOR GLOBAL: FUNNEL LOGIC")
        else:
            print("   🏆 GANADOR GLOBAL: VOLUME VALUE")
        print("="*80)


if __name__ == "__main__":
    main()
