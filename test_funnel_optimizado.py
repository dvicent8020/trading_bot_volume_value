#!/usr/bin/env python3
"""
Optimización de Funnel Logic para mejor equilibrio Retorno/Drawdown.
"""

import logging
import pandas as pd
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.funnel_strategy import FunnelStrategy
from trading_bot.backtester import Backtester

logging.basicConfig(level=logging.WARNING)


def run_funnel_test(data, config, timeframe='4h'):
    """Ejecuta test con Funnel Logic."""
    strategy = FunnelStrategy(
        ema_period=config.get('ema_period', 200),
        rsi_period=14,
        rsi_oversold=config.get('rsi_oversold', 30.0),
        rsi_overbought=config.get('rsi_overbought', 70.0),
        volume_period=20,
        volume_ratio_threshold=config.get('volume_ratio', 1.0),
        delta_confirmation_candles=config.get('delta_candles', 2),
        delta_lookback=3
    )
    
    signals = strategy.generate_signals(data)
    
    backtester = Backtester(
        initial_capital=10000.0,
        commission=0.001,
        stop_loss_pct=config.get('stop_loss_pct', None),
        take_profit_pct=config.get('take_profit_pct', 0.08),
        market_type='futures',
        leverage=config.get('leverage', 10.0),
        trailing_stop_activation=config.get('trailing_activation', 0.05),
        trailing_stop_distance=config.get('trailing_distance', 0.02),
        atr_period=14,
        atr_multiplier=config.get('atr_multiplier', 2.0)
    )
    
    results = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, timeframe=timeframe)
    trades = backtester.get_trades(results)
    
    return {
        'signals': (signals != 0).sum(),
        'return': metrics.get('total_return_pct', 0),
        'sharpe': metrics.get('sharpe_ratio', 0),
        'drawdown': metrics.get('max_drawdown_pct', 0),
        'win_rate': metrics.get('win_rate', 0),
        'trades': len(trades),
        'liquidations': metrics.get('num_liquidations', 0)
    }


def main():
    print("\n" + "="*80)
    print("   OPTIMIZACIÓN DE FUNNEL LOGIC")
    print("   Objetivo: Mejor equilibrio Retorno/Drawdown")
    print("="*80)
    
    # Obtener datos
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data_4h = data_handler.fetch_historical_data(timeframe='4h', days=90)
    
    print(f"\nDatos 4H: {len(data_4h)} velas")
    print(f"Período: {data_4h.index[0]} a {data_4h.index[-1]}")
    
    # Configuraciones a probar
    configs = [
        {
            'name': 'Original (10x, sin SL fijo)',
            'leverage': 10.0,
            'stop_loss_pct': None,
            'atr_multiplier': 2.0,
            'trailing_activation': 0.05,
            'trailing_distance': 0.02,
            'take_profit_pct': 0.08,
        },
        {
            'name': 'Leverage reducido (5x)',
            'leverage': 5.0,
            'stop_loss_pct': None,
            'atr_multiplier': 2.0,
            'trailing_activation': 0.05,
            'trailing_distance': 0.02,
            'take_profit_pct': 0.08,
        },
        {
            'name': 'Leverage 5x + SL 3%',
            'leverage': 5.0,
            'stop_loss_pct': 0.03,  # SL más ajustado
            'atr_multiplier': 1.5,
            'trailing_activation': 0.03,
            'trailing_distance': 0.015,
            'take_profit_pct': 0.06,
        },
        {
            'name': 'Leverage 3x + SL 5% (conservador)',
            'leverage': 3.0,
            'stop_loss_pct': 0.05,
            'atr_multiplier': 2.0,
            'trailing_activation': 0.03,
            'trailing_distance': 0.01,
            'take_profit_pct': 0.10,
        },
        {
            'name': 'Leverage 5x + Trailing ajustado',
            'leverage': 5.0,
            'stop_loss_pct': 0.04,
            'atr_multiplier': 1.5,
            'trailing_activation': 0.02,  # Activación más temprana
            'trailing_distance': 0.01,    # Trailing más cercano
            'take_profit_pct': 0.08,
        },
        {
            'name': 'Leverage 7x + Balance',
            'leverage': 7.0,
            'stop_loss_pct': 0.025,  # SL muy ajustado
            'atr_multiplier': 1.2,
            'trailing_activation': 0.02,
            'trailing_distance': 0.008,
            'take_profit_pct': 0.06,
        },
    ]
    
    print("\n" + "="*80)
    print("RESULTADOS DE OPTIMIZACIÓN")
    print("="*80)
    print(f"\n{'Configuración':<35} {'Retorno':<12} {'Sharpe':<10} {'MaxDD':<12} {'Trades':<8} {'Liq':<6}")
    print("-"*85)
    
    results = []
    for config in configs:
        result = run_funnel_test(data_4h, config, '4h')
        result['name'] = config['name']
        results.append(result)
        
        # Marcar liquidaciones
        liq_mark = '❌' if result['liquidations'] > 0 else '✅'
        print(f"{config['name']:<35} {result['return']:>+9.2f}% {result['sharpe']:>9.2f} {result['drawdown']:>10.2f}% {result['trades']:>6} {liq_mark}")
    
    # Encontrar mejor configuración
    print("\n" + "="*80)
    print("ANÁLISIS")
    print("="*80)
    
    # Mejor retorno
    best_return = max(results, key=lambda x: x['return'])
    print(f"\n🏆 Mejor Retorno: {best_return['name']}")
    print(f"   Retorno: {best_return['return']:+.2f}%, DD: {best_return['drawdown']:.2f}%")
    
    # Mejor Sharpe
    best_sharpe = max(results, key=lambda x: x['sharpe'])
    print(f"\n🏆 Mejor Sharpe: {best_sharpe['name']}")
    print(f"   Sharpe: {best_sharpe['sharpe']:.2f}, DD: {best_sharpe['drawdown']:.2f}%")
    
    # Menor Drawdown con retorno positivo
    positive_results = [r for r in results if r['return'] > 0]
    if positive_results:
        best_dd = max(positive_results, key=lambda x: x['drawdown'])  # más cercano a 0
        print(f"\n🏆 Menor Drawdown (con retorno positivo): {best_dd['name']}")
        print(f"   DD: {best_dd['drawdown']:.2f}%, Retorno: {best_dd['return']:+.2f}%")
    
    # Mejor balance (Retorno / |Drawdown|)
    for r in results:
        if r['drawdown'] != 0:
            r['balance'] = r['return'] / abs(r['drawdown'])
        else:
            r['balance'] = r['return']
    
    best_balance = max(results, key=lambda x: x['balance'])
    print(f"\n🏆 Mejor Balance (Retorno/DD): {best_balance['name']}")
    print(f"   Retorno: {best_balance['return']:+.2f}%, DD: {best_balance['drawdown']:.2f}%, Ratio: {best_balance['balance']:.2f}")
    
    print("\n" + "="*80)
    print("RECOMENDACIÓN PARA FUNNEL LOGIC")
    print("="*80)
    print("""
Para mejor equilibrio Retorno/Drawdown:

1. REDUCIR LEVERAGE: 10x → 5x o 3x
   - Reduce riesgo de liquidación
   - Drawdown más controlado
   
2. AÑADIR STOP LOSS FIJO: 3-5%
   - Protección adicional al ATR
   - Limita pérdidas máximas
   
3. TRAILING STOP MÁS AGRESIVO:
   - Activación: 2-3% (no 5%)
   - Distancia: 1-1.5% (no 2%)
   - Asegura ganancias más rápido
   
4. TAKE PROFIT AJUSTADO:
   - 6-8% en lugar de 8%
   - Más trades cerrados con ganancia
    """)


if __name__ == "__main__":
    main()
