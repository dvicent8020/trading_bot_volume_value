#!/usr/bin/env python3
"""
Script para optimizar parámetros de FunnelStrategy enfocándose en minimizar drawdown.
Prueba diferentes configuraciones en timeframe 4h.
"""

import logging
import sys
import pandas as pd
from typing import Dict, List
from trading_bot import FunnelStrategy, DataHandler, Backtester
from trading_bot.exceptions import TradingBotError

# Configurar logging solo para errores
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest(
    data: pd.DataFrame,
    ema_period: int,
    rsi_oversold: float,
    rsi_overbought: float,
    volume_ratio_threshold: float,
    delta_confirmation_candles: int,
    atr_multiplier: float,
    timeframe: str = '4h'
) -> Dict:
    """Ejecuta un backtest con la configuración especificada."""
    try:
        # Crear estrategia
        strategy = FunnelStrategy(
            ema_period=ema_period,
            rsi_period=14,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
            volume_period=20,
            volume_ratio_threshold=volume_ratio_threshold,
            delta_confirmation_candles=delta_confirmation_candles,
            delta_lookback=3
        )
        
        # Generar señales
        signals = strategy.generate_signals(data)
        
        # Ejecutar backtest
        backtester = Backtester(
            initial_capital=5000.0,
            commission=0.001,
            stop_loss_pct=None,
            take_profit_pct=0.08,
            market_type='futures',
            leverage=10.0,
            trailing_stop_activation=0.05,
            trailing_stop_distance=0.02,
            atr_period=14,
            atr_multiplier=atr_multiplier
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        trades = backtester.get_trades(results)
        
        return {
            'success': True,
            'metrics': metrics,
            'num_signals': (signals != 0).sum(),
            'num_trades': len(trades),
            'ema_period': ema_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'volume_ratio_threshold': volume_ratio_threshold,
            'delta_confirmation_candles': delta_confirmation_candles,
            'atr_multiplier': atr_multiplier
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'ema_period': ema_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'volume_ratio_threshold': volume_ratio_threshold,
            'delta_confirmation_candles': delta_confirmation_candles,
            'atr_multiplier': atr_multiplier
        }


def main():
    """Función principal."""
    print("="*80)
    print("OPTIMIZACIÓN DE FUNNEL STRATEGY - ENFOQUE EN DRAWDOWN")
    print("="*80)
    print("\nTimeframe: 4h, Período: 90 días")
    print("Objetivo: Minimizar Maximum Drawdown")
    print("="*80)
    
    # Descargar datos una vez
    print("\nDescargando datos históricos...")
    data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
    data = data_handler.fetch_historical_data(timeframe='4h', days=90)
    data_handler.validate_data(data)
    print(f"✓ Datos descargados: {len(data)} velas")
    
    # Configuraciones a probar
    configs = []
    
    # Base: EMA 200, RSI 30/70
    base_configs = [
        # Variar ATR multiplier y Volume Ratio Threshold
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 0.8, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.0},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 0.8, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.5},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 0.8, 'delta_confirmation_candles': 3, 'atr_multiplier': 2.0},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.0},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.5},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 3, 'atr_multiplier': 2.0},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.2, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.5},
        
        # Variar Delta Confirmation Candles
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 2, 'atr_multiplier': 1.5},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 4, 'atr_multiplier': 1.5},
        
        # Variar RSI thresholds (más conservador)
        {'ema_period': 200, 'rsi_oversold': 25.0, 'rsi_overbought': 75.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.5},
        {'ema_period': 200, 'rsi_oversold': 35.0, 'rsi_overbought': 65.0, 
         'volume_ratio_threshold': 1.0, 'delta_confirmation_candles': 3, 'atr_multiplier': 1.5},
        
        # Combinaciones más conservadoras
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.2, 'delta_confirmation_candles': 4, 'atr_multiplier': 1.0},
        {'ema_period': 200, 'rsi_oversold': 30.0, 'rsi_overbought': 70.0, 
         'volume_ratio_threshold': 1.2, 'delta_confirmation_candles': 4, 'atr_multiplier': 1.5},
    ]
    
    configs.extend(base_configs)
    
    print(f"\nTotal de configuraciones a probar: {len(configs)}")
    print("="*80)
    
    results = []
    for i, config in enumerate(configs, 1):
        config_str = (
            f"EMA{config['ema_period']}_RSI{config['rsi_oversold']:.0f}-{config['rsi_overbought']:.0f}_"
            f"VR{config['volume_ratio_threshold']:.1f}_Delta{config['delta_confirmation_candles']}_"
            f"ATR{config['atr_multiplier']:.1f}"
        )
        
        print(f"[{i:2d}/{len(configs)}] Probando: {config_str[:60]}...", end=" ", flush=True)
        
        result = run_backtest(
            data=data,
            timeframe='4h',
            **config
        )
        
        results.append(result)
        
        if result['success']:
            sharpe = result['metrics'].get('sharpe_ratio', 0)
            total_return = result['metrics'].get('total_return_pct', 0)
            max_dd = result['metrics'].get('max_drawdown_pct', 0)
            num_signals = result['num_signals']
            num_trades = result['num_trades']
            
            print(f"✓ DD: {max_dd:7.2f}% | Sharpe: {sharpe:5.2f} | Retorno: {total_return:7.2f}% | "
                  f"Señales: {num_signals:2d} | Trades: {num_trades:2d}")
        else:
            print(f"✗ Error: {result.get('error', 'Unknown')}")
    
    # Analizar resultados
    print("\n" + "="*80)
    print("ANÁLISIS DE RESULTADOS - ENFOQUE EN DRAWDOWN")
    print("="*80)
    
    successful = [r for r in results if r.get('success')]
    
    if not successful:
        print("No se completaron pruebas exitosas.")
        return 1
    
    # Ordenar por drawdown (menor valor absoluto es mejor, es decir, menos negativo)
    sorted_by_dd = sorted(successful, key=lambda x: abs(x['metrics'].get('max_drawdown_pct', 999)))
    
    print("\nTOP 10 CONFIGURACIONES CON MENOR DRAWDOWN:")
    print("-"*80)
    print(f"{'#':<3} {'Configuración':<50} {'DD %':<10} {'Sharpe':<8} {'Retorno %':<12} {'Señales':<8} {'Trades':<8}")
    print("-"*80)
    
    for i, r in enumerate(sorted_by_dd[:10], 1):
        config_str = (
            f"EMA{r['ema_period']}_RSI{r['rsi_oversold']:.0f}-{r['rsi_overbought']:.0f}_"
            f"VR{r['volume_ratio_threshold']:.1f}_Delta{r['delta_confirmation_candles']}_"
            f"ATR{r['atr_multiplier']:.1f}"
        )
        
        dd = r['metrics'].get('max_drawdown_pct', 0)
        sharpe = r['metrics'].get('sharpe_ratio', 0)
        ret = r['metrics'].get('total_return_pct', 0)
        signals = r['num_signals']
        trades = r['num_trades']
        
        print(f"{i:<3} {config_str:<50} {dd:>8.2f}% {sharpe:>7.2f} {ret:>11.2f}% {signals:>7} {trades:>7}")
    
    # Mejor configuración
    best = sorted_by_dd[0]
    print("\n" + "="*80)
    print("MEJOR CONFIGURACIÓN (MENOR DRAWDOWN):")
    print("="*80)
    print(f"EMA Period: {best['ema_period']}")
    print(f"RSI Oversold: {best['rsi_oversold']}")
    print(f"RSI Overbought: {best['rsi_overbought']}")
    print(f"Volume Ratio Threshold: {best['volume_ratio_threshold']}")
    print(f"Delta Confirmation Candles: {best['delta_confirmation_candles']}")
    print(f"ATR Multiplier: {best['atr_multiplier']}")
    print("\nMétricas:")
    metrics = best['metrics']
    print(f"  - Maximum Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"  - Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  - Retorno Total: {metrics.get('total_return_pct', 0):.2f}%")
    print(f"  - Retorno Anualizado: {metrics.get('annualized_return_pct', 0):.2f}%")
    print(f"  - Total Operaciones: {best['num_trades']}")
    print(f"  - Total Señales: {best['num_signals']}")
    print("="*80)
    
    # Análisis de correlaciones
    print("\nANÁLISIS DE CORRELACIONES:")
    print("-"*80)
    
    # Agrupar por parámetros y calcular promedio de drawdown
    param_analysis = {}
    
    for r in successful:
        key = f"ATR{r['atr_multiplier']:.1f}"
        if key not in param_analysis:
            param_analysis[key] = []
        param_analysis[key].append(r['metrics'].get('max_drawdown_pct', 0))
    
    print("\nDrawdown promedio por ATR Multiplier:")
    for atr_val in sorted(param_analysis.keys()):
        avg_dd = sum(param_analysis[atr_val]) / len(param_analysis[atr_val])
        print(f"  {atr_val}: {avg_dd:.2f}% (promedio de {len(param_analysis[atr_val])} configuraciones)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
