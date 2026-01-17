#!/usr/bin/env python3
"""
Pruebas completas de Funnel Logic con configuración optimizada.
Timeframes: 15m, 1h, 4h, 1d
Períodos: 90 días, 365 días
"""

import logging
import pandas as pd
from datetime import datetime

from trading_bot.data_handler import DataHandler
from trading_bot.funnel_strategy import FunnelStrategy
from trading_bot.backtester import Backtester

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_optimized_config(timeframe: str) -> dict:
    """
    Retorna la configuración optimizada según el timeframe.
    
    Recomendaciones aplicadas:
    - Leverage reducido: 10x → 5x (balance óptimo)
    - Stop Loss fijo adicional: 4%
    - Trailing más agresivo: activación 3%, distancia 1.5%
    - Take Profit ajustado: 8%
    """
    # Configuración base optimizada
    base_config = {
        'leverage': 5.0,
        'stop_loss_pct': 0.04,  # 4% fijo + ATR
        'atr_multiplier': 1.8,
        'trailing_activation': 0.03,  # 3% (más agresivo que 5%)
        'trailing_distance': 0.015,   # 1.5% (más ajustado que 2%)
        'take_profit_pct': 0.08,
        'ema_period': 200,
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_ratio': 1.0,
        'delta_candles': 2,
    }
    
    # Ajustes por timeframe
    if timeframe == '15m':
        # Timeframes cortos: más conservador
        base_config['leverage'] = 3.0
        base_config['stop_loss_pct'] = 0.02  # 2%
        base_config['trailing_activation'] = 0.02
        base_config['trailing_distance'] = 0.01
        base_config['take_profit_pct'] = 0.04
        base_config['ema_period'] = 100  # EMA más corta
        
    elif timeframe == '1h':
        base_config['leverage'] = 4.0
        base_config['stop_loss_pct'] = 0.03
        base_config['trailing_activation'] = 0.025
        base_config['trailing_distance'] = 0.012
        base_config['take_profit_pct'] = 0.06
        base_config['ema_period'] = 150
        
    elif timeframe == '4h':
        # Ya optimizado - balance óptimo
        pass
        
    elif timeframe == '1d':
        # Timeframes largos: más espacio
        base_config['leverage'] = 5.0
        base_config['stop_loss_pct'] = 0.05
        base_config['trailing_activation'] = 0.04
        base_config['trailing_distance'] = 0.02
        base_config['take_profit_pct'] = 0.10
        base_config['ema_period'] = 100  # Menos datos disponibles
    
    return base_config


def run_funnel_test(data: pd.DataFrame, config: dict, timeframe: str) -> dict:
    """Ejecuta test con Funnel Logic optimizado."""
    # Ajustar EMA si hay pocos datos
    ema_period = min(config['ema_period'], len(data) - 30)
    if ema_period < 50:
        ema_period = max(30, len(data) // 3)
    
    try:
        strategy = FunnelStrategy(
            ema_period=ema_period,
            rsi_period=14,
            rsi_oversold=config['rsi_oversold'],
            rsi_overbought=config['rsi_overbought'],
            volume_period=20,
            volume_ratio_threshold=config['volume_ratio'],
            delta_confirmation_candles=config['delta_candles'],
            delta_lookback=3
        )
        
        signals = strategy.generate_signals(data)
        
        backtester = Backtester(
            initial_capital=10000.0,
            commission=0.001,
            stop_loss_pct=config['stop_loss_pct'],
            take_profit_pct=config['take_profit_pct'],
            market_type='futures',
            leverage=config['leverage'],
            trailing_stop_activation=config['trailing_activation'],
            trailing_stop_distance=config['trailing_distance'],
            atr_period=14,
            atr_multiplier=config['atr_multiplier']
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        trades = backtester.get_trades(results)
        
        return {
            'success': True,
            'signals': int((signals != 0).sum()),
            'long_signals': int((signals == 1).sum()),
            'short_signals': int((signals == -1).sum()),
            'return': metrics.get('total_return_pct', 0),
            'sharpe': metrics.get('sharpe_ratio', 0),
            'drawdown': metrics.get('max_drawdown_pct', 0),
            'win_rate': metrics.get('win_rate', 0),
            'trades': len(trades),
            'liquidations': metrics.get('num_liquidations', 0),
            'leverage': config['leverage'],
            'stop_loss': config['stop_loss_pct'] * 100
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'return': 0,
            'sharpe': 0,
            'drawdown': 0,
            'win_rate': 0,
            'trades': 0
        }


def main():
    print("\n" + "="*90)
    print("   PRUEBAS COMPLETAS: FUNNEL LOGIC OPTIMIZADO")
    print("="*90)
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\n   Configuración optimizada aplicada:")
    print("   - Leverage: 3-5x según timeframe")
    print("   - Stop Loss fijo: 2-5% + ATR")
    print("   - Trailing: Activación 2-4%, Distancia 1-2%")
    print("   - Take Profit: 4-10% según timeframe")
    print("="*90)
    
    # Configuraciones de prueba
    tests = [
        {'timeframe': '15m', 'days': 90},
        {'timeframe': '1h', 'days': 90},
        {'timeframe': '4h', 'days': 90},
        {'timeframe': '4h', 'days': 365},
        {'timeframe': '1d', 'days': 90},
        {'timeframe': '1d', 'days': 365},
    ]
    
    all_results = []
    
    for test in tests:
        tf = test['timeframe']
        days = test['days']
        
        print(f"\n{'─'*90}")
        print(f"  TEST: {tf} - {days} días")
        print(f"{'─'*90}")
        
        # Obtener datos
        data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
        data = data_handler.fetch_historical_data(timeframe=tf, days=days)
        
        if data is None or data.empty:
            print(f"  ❌ Error obteniendo datos")
            continue
        
        print(f"  📊 Datos: {len(data)} velas")
        print(f"  📅 Período: {data.index[0].strftime('%Y-%m-%d')} a {data.index[-1].strftime('%Y-%m-%d')}")
        
        # Obtener configuración optimizada
        config = get_optimized_config(tf)
        print(f"  ⚙️  Config: Leverage {config['leverage']}x, SL {config['stop_loss_pct']*100}%, TP {config['take_profit_pct']*100}%")
        
        # Ejecutar test
        result = run_funnel_test(data, config, tf)
        result['timeframe'] = tf
        result['days'] = days
        all_results.append(result)
        
        if result.get('success', False):
            # Indicadores de estado
            liq = '❌ LIQ' if result.get('liquidations', 0) > 0 else '✅'
            ret_icon = '🟢' if result['return'] > 0 else '🔴'
            dd_icon = '🟢' if result['drawdown'] > -30 else '🟡' if result['drawdown'] > -50 else '🔴'
            
            print(f"\n  RESULTADOS:")
            print(f"  {ret_icon} Retorno: {result['return']:+.2f}%")
            print(f"  📈 Sharpe: {result['sharpe']:.2f}")
            print(f"  {dd_icon} Max Drawdown: {result['drawdown']:.2f}%")
            print(f"  🎯 Win Rate: {result['win_rate']:.1f}%")
            print(f"  📊 Trades: {result['trades']} (L:{result.get('long_signals',0)}, S:{result.get('short_signals',0)})")
            print(f"  {liq}")
        else:
            print(f"  ❌ Error: {result.get('error', 'Unknown')}")
    
    # Resumen
    print("\n" + "="*90)
    print("                           RESUMEN DE RESULTADOS")
    print("="*90)
    print(f"\n{'TF':<6} {'Días':<6} {'Leverage':<10} {'Retorno':<12} {'Sharpe':<10} {'MaxDD':<12} {'WR':<8} {'Trades':<8}")
    print("─"*90)
    
    for r in all_results:
        if r.get('success', False):
            lev = f"{r.get('leverage', '?')}x"
            print(f"{r['timeframe']:<6} {r['days']:<6} {lev:<10} {r['return']:>+9.2f}% {r['sharpe']:>9.2f} {r['drawdown']:>10.2f}% {r['win_rate']:>6.1f}% {r['trades']:>6}")
        else:
            print(f"{r['timeframe']:<6} {r['days']:<6} {'ERROR':<10}")
    
    print("─"*90)
    
    # Estadísticas
    successful = [r for r in all_results if r.get('success', False)]
    if successful:
        avg_return = sum(r['return'] for r in successful) / len(successful)
        avg_sharpe = sum(r['sharpe'] for r in successful) / len(successful)
        avg_dd = sum(r['drawdown'] for r in successful) / len(successful)
        positive = len([r for r in successful if r['return'] > 0])
        
        print(f"\n📊 ESTADÍSTICAS GLOBALES:")
        print(f"   Retorno Promedio: {avg_return:+.2f}%")
        print(f"   Sharpe Promedio: {avg_sharpe:.2f}")
        print(f"   Drawdown Promedio: {avg_dd:.2f}%")
        print(f"   Tests Positivos: {positive}/{len(successful)}")
    
    # Mejores resultados
    if successful:
        print("\n" + "="*90)
        print("                           MEJORES RESULTADOS")
        print("="*90)
        
        best_return = max(successful, key=lambda x: x['return'])
        print(f"\n🏆 Mejor Retorno: {best_return['timeframe']} {best_return['days']}d")
        print(f"   Retorno: {best_return['return']:+.2f}%, Sharpe: {best_return['sharpe']:.2f}, DD: {best_return['drawdown']:.2f}%")
        
        best_sharpe = max(successful, key=lambda x: x['sharpe'])
        print(f"\n🏆 Mejor Sharpe: {best_sharpe['timeframe']} {best_sharpe['days']}d")
        print(f"   Sharpe: {best_sharpe['sharpe']:.2f}, Retorno: {best_sharpe['return']:+.2f}%, DD: {best_sharpe['drawdown']:.2f}%")
        
        # Menor DD con retorno positivo
        positive_results = [r for r in successful if r['return'] > 0]
        if positive_results:
            best_dd = max(positive_results, key=lambda x: x['drawdown'])
            print(f"\n🏆 Mejor Balance (Retorno positivo + menor DD): {best_dd['timeframe']} {best_dd['days']}d")
            print(f"   Retorno: {best_dd['return']:+.2f}%, DD: {best_dd['drawdown']:.2f}%, Sharpe: {best_dd['sharpe']:.2f}")
    
    print("\n" + "="*90)


if __name__ == "__main__":
    main()
