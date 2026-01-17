#!/usr/bin/env python3
"""
Script de pruebas para Smart Trailing Stop (Híbrido Inteligente).

Compara el rendimiento del Smart Trailing vs Trailing tradicional
en múltiples timeframes (15m, 1h, 4h, 1d).
"""

import logging
import pandas as pd
from datetime import datetime
from trading_bot import VolumeValueStrategy, DataHandler, Backtester
from trading_bot.exceptions import TradingBotError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_test(timeframe: str, days: int, use_smart_trailing: bool, config_name: str):
    """
    Ejecuta un backtest con la configuración especificada.
    
    Args:
        timeframe: Temporalidad (15m, 1h, 4h, 1d)
        days: Días de datos históricos
        use_smart_trailing: Si usar Smart Trailing Stop
        config_name: Nombre de la configuración
        
    Returns:
        Dict con métricas
    """
    try:
        # Obtener datos
        data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        # Configurar estrategia con parámetros óptimos
        strategy = VolumeValueStrategy(
            vwap_period_days=7,
            volume_profile_period=7,
            value_area_percent=0.68,
            delta_lookback=20,
            volatility_threshold=3.0,
            min_volume_period=20,
            lvn_lookback=50,
            market_regime_enabled=True,
            adx_period=14,
            adx_threshold=25,
            adx_slope_enabled=True,
            adx_slope_period=5,
            use_normalized_cvd=True,
            signal_cooldown=5,
            disable_longs=False,
            disable_shorts=False
        )
        
        signals = strategy.generate_signals(data)
        
        # Configurar backtester
        backtester_params = {
            'initial_capital': 5000,
            'commission': 0.001,
            'market_type': 'futures',
            'leverage': 2.0,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.06,
            'trailing_stop_activation': 0.015,
            'atr_period': 14,
            'atr_multiplier': 1.5,
        }
        
        if use_smart_trailing:
            # Smart Trailing Stop habilitado
            backtester_params.update({
                'smart_trailing_enabled': True,
                'smart_trailing_atr_base': 2.0,
                'smart_trailing_profit_phases': True,
                'smart_trailing_time_decay': True,
                'smart_trailing_breakeven_threshold': 0.03,
                'trailing_stop_distance': None,  # No usar porcentaje fijo
            })
        else:
            # Trailing tradicional
            backtester_params.update({
                'smart_trailing_enabled': False,
                'trailing_stop_distance': 0.005,  # 0.5% fijo
            })
        
        backtester = Backtester(**backtester_params)
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        # Obtener trades para análisis
        trades_df = backtester.get_trades(results)
        
        # Calcular métricas adicionales de los trades
        if not trades_df.empty:
            avg_win = trades_df[trades_df['P&L ($)'] > 0]['P&L (%)'].mean() if (trades_df['P&L ($)'] > 0).any() else 0
            avg_loss = trades_df[trades_df['P&L ($)'] < 0]['P&L (%)'].mean() if (trades_df['P&L ($)'] < 0).any() else 0
            max_win = trades_df['P&L (%)'].max() if not trades_df.empty else 0
            max_loss = trades_df['P&L (%)'].min() if not trades_df.empty else 0
        else:
            avg_win = avg_loss = max_win = max_loss = 0
        
        return {
            'config': config_name,
            'timeframe': timeframe,
            'days': days,
            'smart_trailing': use_smart_trailing,
            'signals': (signals == 1).sum() + (signals == -1).sum(),
            'trades': metrics.get('num_trades', 0),
            'return_pct': metrics.get('total_return_pct', 0),
            'sharpe': metrics.get('sharpe_ratio', 0),
            'drawdown': metrics.get('max_drawdown_pct', 0),
            'win_rate': metrics.get('win_rate', 0) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss,
            'profit_factor': metrics.get('profit_factor', 0),
        }
        
    except Exception as e:
        logger.error(f"Error en {config_name}: {e}")
        return {
            'config': config_name,
            'timeframe': timeframe,
            'days': days,
            'smart_trailing': use_smart_trailing,
            'error': str(e)
        }


def main():
    """Ejecuta las pruebas comparativas."""
    print("\n" + "="*100)
    print("PRUEBAS COMPARATIVAS: SMART TRAILING STOP vs TRAILING TRADICIONAL")
    print("BTC/USDT - Múltiples Timeframes - 90 días")
    print("="*100)
    
    # Configuraciones de prueba
    timeframes = ['15m', '1h', '4h', '1d']
    days = 90
    
    all_results = []
    
    for tf in timeframes:
        print(f"\n{'='*60}")
        print(f"📊 TIMEFRAME: {tf.upper()}")
        print('='*60)
        
        # Obtener datos una vez para este timeframe
        print(f"\n📊 Obteniendo datos de Binance ({tf}, {days} días)...")
        
        # Test 1: Trailing Tradicional (0.5% fijo)
        result_traditional = run_test(
            timeframe=tf,
            days=days,
            use_smart_trailing=False,
            config_name='Tradicional (0.5%)'
        )
        all_results.append(result_traditional)
        
        if 'error' not in result_traditional:
            print(f"   Tradicional (0.5%)      | {result_traditional['trades']:3d} ops | "
                  f"{result_traditional['return_pct']:7.1f}% | Sharpe {result_traditional['sharpe']:5.2f} | "
                  f"DD {result_traditional['drawdown']:6.1f}% | WR {result_traditional['win_rate']:.0f}% | "
                  f"AvgWin {result_traditional['avg_win']:.1f}% | MaxWin {result_traditional['max_win']:.1f}%")
        
        # Test 2: Smart Trailing (Híbrido)
        result_smart = run_test(
            timeframe=tf,
            days=days,
            use_smart_trailing=True,
            config_name='Smart Trailing'
        )
        all_results.append(result_smart)
        
        if 'error' not in result_smart:
            print(f"   Smart Trailing          | {result_smart['trades']:3d} ops | "
                  f"{result_smart['return_pct']:7.1f}% | Sharpe {result_smart['sharpe']:5.2f} | "
                  f"DD {result_smart['drawdown']:6.1f}% | WR {result_smart['win_rate']:.0f}% | "
                  f"AvgWin {result_smart['avg_win']:.1f}% | MaxWin {result_smart['max_win']:.1f}%")
        
        # Comparación
        if 'error' not in result_traditional and 'error' not in result_smart:
            ret_diff = result_smart['return_pct'] - result_traditional['return_pct']
            avg_win_diff = result_smart['avg_win'] - result_traditional['avg_win']
            max_win_diff = result_smart['max_win'] - result_traditional['max_win']
            
            print(f"\n   📈 Diferencia Smart vs Tradicional:")
            print(f"      Retorno: {ret_diff:+.1f}%")
            print(f"      Avg Win: {avg_win_diff:+.2f}%")
            print(f"      Max Win: {max_win_diff:+.2f}%")
    
    # Resumen Final
    print("\n" + "="*100)
    print("RESUMEN COMPARATIVO")
    print("="*100)
    
    # Crear DataFrame para análisis
    df_results = pd.DataFrame([r for r in all_results if 'error' not in r])
    
    if not df_results.empty:
        print("\n{:12} {:20} {:>8} {:>10} {:>8} {:>8} {:>8} {:>10}".format(
            "Timeframe", "Config", "Trades", "Return", "Sharpe", "DD", "WinRate", "Avg Win"
        ))
        print("-" * 100)
        
        for _, row in df_results.iterrows():
            print(f"{row['timeframe']:12} {row['config']:20} {row['trades']:8d} "
                  f"{row['return_pct']:9.1f}% {row['sharpe']:8.2f} {row['drawdown']:7.1f}% "
                  f"{row['win_rate']:7.0f}% {row['avg_win']:9.2f}%")
        
        print("-" * 100)
        
        # Comparación por tipo de trailing
        print("\n📊 PROMEDIO POR TIPO DE TRAILING:")
        for smart in [False, True]:
            subset = df_results[df_results['smart_trailing'] == smart]
            if not subset.empty:
                config_type = "Smart Trailing" if smart else "Tradicional"
                print(f"\n   {config_type}:")
                print(f"      Retorno promedio: {subset['return_pct'].mean():.1f}%")
                print(f"      Sharpe promedio:  {subset['sharpe'].mean():.2f}")
                print(f"      DD promedio:      {subset['drawdown'].mean():.1f}%")
                print(f"      Win Rate prom:    {subset['win_rate'].mean():.0f}%")
                print(f"      Avg Win prom:     {subset['avg_win'].mean():.2f}%")
                print(f"      Max Win prom:     {subset['max_win'].mean():.2f}%")
        
        # Mejor configuración
        print("\n🏆 MEJOR CONFIGURACIÓN POR MÉTRICA:")
        best_return = df_results.loc[df_results['return_pct'].idxmax()]
        best_sharpe = df_results.loc[df_results['sharpe'].idxmax()]
        best_avg_win = df_results.loc[df_results['avg_win'].idxmax()]
        
        print(f"   Mejor Retorno: {best_return['config']} en {best_return['timeframe']} ({best_return['return_pct']:.1f}%)")
        print(f"   Mejor Sharpe:  {best_sharpe['config']} en {best_sharpe['timeframe']} ({best_sharpe['sharpe']:.2f})")
        print(f"   Mejor Avg Win: {best_avg_win['config']} en {best_avg_win['timeframe']} ({best_avg_win['avg_win']:.2f}%)")
    
    print("\n" + "="*100)
    print("Pruebas completadas")
    print("="*100)


if __name__ == "__main__":
    main()
