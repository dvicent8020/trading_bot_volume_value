#!/usr/bin/env python3
"""
Script para probar las mejoras sugeridas por el experto en trading algorítmico.
Compara cada mejora de forma individual y combinada contra un baseline.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta

from trading_bot.data_handler import DataHandler
from trading_bot.volume_value_strategy import VolumeValueStrategy
from trading_bot.backtester import Backtester

def setup_logging(level='INFO'):
    """Configura el logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_test(data: pd.DataFrame, config: dict, logger) -> dict:
    """
    Ejecuta un backtest con la configuración dada.
    
    Args:
        data: DataFrame con datos OHLCV
        config: Diccionario de configuración
        logger: Logger para mensajes
        
    Returns:
        Diccionario con métricas del backtest
    """
    try:
        # Crear estrategia con parámetros de la configuración
        strategy = VolumeValueStrategy(
            vwap_period_days=config.get('vwap_period_days', 7),
            volume_profile_period=config.get('volume_profile_period', 7),
            delta_lookback=config.get('delta_lookback', 20),
            lvn_lookback=config.get('lvn_lookback', 50),
            market_regime_enabled=config.get('market_regime_enabled', True),
            adx_period=config.get('adx_period', 14),
            adx_threshold=config.get('adx_threshold', 25),
            signal_cooldown=config.get('signal_cooldown', 5),
            # Sin restricción de LONGs ni SHORTs
            disable_longs=config.get('disable_longs', False),
            disable_shorts=config.get('disable_shorts', False),
            # Mejoras del experto
            use_normalized_cvd=config.get('use_normalized_cvd', False),
            dynamic_vp_period=config.get('dynamic_vp_period', 7),
            adx_slope_enabled=config.get('adx_slope_enabled', False)
        )
        
        # Generar señales (retorna una Series con 1=LONG, -1=SHORT, 0=nada)
        signals = strategy.generate_signals(data)
        
        if signals is None or signals.empty:
            return None
        
        # Contar señales
        long_signals = (signals == 1).sum()
        short_signals = (signals == -1).sum()
        logger.debug(f"Señales: {long_signals} LONG, {short_signals} SHORT")
            
        # Crear backtester
        backtester = Backtester(
            initial_capital=config.get('initial_capital', 5000),
            commission=config.get('commission', 0.001),
            stop_loss_pct=config.get('stop_loss_pct', 0.05),
            take_profit_pct=config.get('take_profit_pct', 0.08),
            market_type='futures',
            leverage=config.get('leverage', 3.0),
            trailing_stop_activation=config.get('trailing_stop_activation', 0.03),
            trailing_stop_distance=config.get('trailing_stop_distance', 0.01),
            atr_period=config.get('atr_period', 14),
            atr_multiplier=config.get('atr_multiplier', 1.5),
            # Mejora del experto: Trailing Stop basado en ATR
            trailing_atr_enabled=config.get('trailing_atr_enabled', False),
            trailing_atr_multiplier=config.get('trailing_atr_multiplier', 2.5),
            # Exhaustion exit
            exhaustion_exit_enabled=config.get('exhaustion_exit_enabled', False),
            exhaustion_lookback=config.get('exhaustion_lookback', 10)
        )
        
        # Verificar alineación de índices
        logger.debug(f"Data index: {data.index[:3]}...{data.index[-3:]}")
        logger.debug(f"Signals index: {signals.index[:3]}...{signals.index[-3:]}")
        logger.debug(f"Señales no cero: {(signals != 0).sum()}")
        
        # Ejecutar backtest (pasamos el DataFrame original con OHLCV y las señales)
        results = backtester.run_backtest(data, signals)
        
        # Debug de resultados
        if results is not None:
            logger.debug(f"Results shape: {results.shape}, columns: {results.columns.tolist()}")
        
        if results is None:
            return None
            
        metrics = backtester.calculate_metrics(results)
        
        # Contar señales generadas
        long_signals = (signals == 1).sum()
        short_signals = (signals == -1).sum()
        
        return {
            'return_pct': metrics.get('total_return_pct', 0),  # Usar total_return_pct
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown_pct', 0),  # Usar max_drawdown_pct
            'win_rate': metrics.get('win_rate', 0),
            'total_trades': metrics.get('num_trades', 0),  # Usar num_trades
            'num_liquidations': metrics.get('num_liquidations', 0),
            'final_capital': metrics.get('final_capital', 0),
            'long_signals': long_signals,
            'short_signals': short_signals
        }
        
    except Exception as e:
        logger.error(f"Error en backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Función principal para ejecutar pruebas comparativas."""
    setup_logging('WARNING')  # Reducir verbosidad
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # Silenciar logs muy verbosos
    logging.getLogger('trading_bot.volume_value_strategy').setLevel(logging.WARNING)
    logging.getLogger('trading_bot.backtester').setLevel(logging.WARNING)
    
    print("\n" + "="*80)
    print("PRUEBAS COMPARATIVAS - OPTIMIZACIÓN DE DRAWDOWN")
    print("BTC/USDT - Temporalidades cortas (15m, 1h) - 90 días")
    print("Objetivo: Drawdown < 20-30%")
    print("="*80)
    
    # Configuraciones de prueba - temporalidades cortas
    test_scenarios = [
        {'timeframe': '15m', 'days': 90, 'label': '15m - 90 días'},
        {'timeframe': '1h', 'days': 90, 'label': '1H - 90 días'},
    ]
    
    all_results = {}
    
    for scenario in test_scenarios:
        print(f"\n{'='*80}")
        print(f"📊 ESCENARIO: {scenario['label']}")
        print("="*80)
        
        # Obtener datos
        print(f"\n📊 Obteniendo datos de Binance ({scenario['timeframe']}, {scenario['days']} días)...")
        data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
        
        data = data_handler.fetch_historical_data(
            timeframe=scenario['timeframe'],
            days=scenario['days']
        )
        
        if data is None or data.empty:
            print("❌ Error obteniendo datos de Binance")
            continue
            
        print(f"✅ Datos obtenidos: {len(data)} velas")
        print(f"   Período: {data.index[0]} a {data.index[-1]}")
        
        # Ejecutar pruebas para este escenario
        scenario_results = run_scenario_tests(data, scenario, logger)
        all_results[scenario['label']] = scenario_results
    
    # Mostrar resumen final
    print_final_summary(all_results)


def run_scenario_tests(data: pd.DataFrame, scenario: dict, logger) -> dict:
    """Ejecuta todas las pruebas para un escenario específico."""
    
    # Configuración base optimizada con ADX Slope (CRÍTICO)
    base_config = {
        # Parámetros de la estrategia
        'vwap_period_days': 7,
        'volume_profile_period': 7,
        'delta_lookback': 20,
        'lvn_lookback': 50,
        'market_regime_enabled': True,
        'adx_period': 14,
        'adx_threshold': 25,
        'signal_cooldown': 5,
        'disable_longs': False,
        'disable_shorts': False,
        # Parámetros del backtester - valores por defecto
        'initial_capital': 5000,
        'commission': 0.001,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.06,
        'leverage': 2.0,
        'trailing_stop_activation': 0.015,
        'trailing_stop_distance': 0.005,
        'atr_period': 14,
        'atr_multiplier': 1.5,
        # Mejoras del experto - ADX Slope HABILITADO (crítico)
        'use_normalized_cvd': True,
        'dynamic_vp_period': 7,
        'adx_slope_enabled': True,
        'trailing_atr_enabled': False
    }
    
    # Configuraciones por LEVERAGE (3x, 5x, 10x)
    # Fórmula: A mayor leverage, stops más ajustados
    test_configs = {
        # === LEVERAGE 3x ===
        '3x Óptimo': {
            'leverage': 3.0, 
            'stop_loss_pct': 0.02,          # 2%
            'trailing_stop_activation': 0.015,
            'trailing_stop_distance': 0.005,
        },
        '3x Conservador': {
            'leverage': 3.0, 
            'stop_loss_pct': 0.015,         # 1.5%
            'trailing_stop_activation': 0.012,
            'trailing_stop_distance': 0.004,
        },
        # === LEVERAGE 5x ===
        '5x Óptimo': {
            'leverage': 5.0, 
            'stop_loss_pct': 0.015,         # 1.5%
            'trailing_stop_activation': 0.012,
            'trailing_stop_distance': 0.004,
        },
        '5x Conservador': {
            'leverage': 5.0, 
            'stop_loss_pct': 0.012,         # 1.2%
            'trailing_stop_activation': 0.010,
            'trailing_stop_distance': 0.003,
        },
        # === LEVERAGE 10x ===
        '10x Óptimo': {
            'leverage': 10.0, 
            'stop_loss_pct': 0.008,         # 0.8%
            'trailing_stop_activation': 0.008,
            'trailing_stop_distance': 0.003,
        },
        '10x Ultra-tight': {
            'leverage': 10.0, 
            'stop_loss_pct': 0.006,         # 0.6%
            'trailing_stop_activation': 0.006,
            'trailing_stop_distance': 0.002,
        },
    }
    
    results = {}
    
    for name, overrides in test_configs.items():
        # Crear configuración combinada
        config = base_config.copy()
        config.update(overrides)
        
        # Ejecutar test
        result = run_test(data, config, logger)
        
        if result:
            results[name] = result
            print(f"   {name:<25} | {result['long_signals']:>3}L/{result['short_signals']:<3}S | {result['total_trades']:>3} ops | {result['return_pct']:>8.1f}% | Sharpe {result['sharpe_ratio']:>5.2f} | DD {result['max_drawdown']:>6.1f}%")
        else:
            print(f"   {name:<25} | ❌ Error")
    
    return results


def print_final_summary(all_results: dict):
    """Imprime resumen final de todas las pruebas."""
    print("\n" + "="*100)
    print("RESUMEN FINAL - TODAS LAS CONFIGURACIONES")
    print("="*100)
    
    # Tabla comparativa por escenario
    print(f"\n{'Escenario':<20} {'Config':<25} {'Señales':>10} {'Ops':>6} {'Retorno':>10} {'Sharpe':>8} {'Drawdown':>10}")
    print("-" * 100)
    
    best_overall = None
    best_return = float('-inf')
    best_sharpe_config = None
    best_sharpe = float('-inf')
    
    for scenario, results in all_results.items():
        for config_name, metrics in results.items():
            signals_str = f"{metrics['long_signals']}L/{metrics['short_signals']}S"
            print(f"{scenario:<20} {config_name:<25} {signals_str:>10} {metrics['total_trades']:>6} {metrics['return_pct']:>9.1f}% {metrics['sharpe_ratio']:>8.2f} {metrics['max_drawdown']:>9.1f}%")
            
            # Track mejores
            if metrics['return_pct'] > best_return:
                best_return = metrics['return_pct']
                best_overall = (scenario, config_name, metrics)
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_sharpe_config = (scenario, config_name, metrics)
        print("-" * 100)
    
    # Mejores configuraciones
    print("\n" + "="*100)
    print("🏆 MEJORES CONFIGURACIONES")
    print("="*100)
    
    if best_overall:
        print(f"\n📈 MEJOR RETORNO:")
        print(f"   Escenario: {best_overall[0]}")
        print(f"   Config: {best_overall[1]}")
        print(f"   Retorno: {best_overall[2]['return_pct']:.2f}%")
        print(f"   Sharpe: {best_overall[2]['sharpe_ratio']:.2f}")
        print(f"   Drawdown: {best_overall[2]['max_drawdown']:.2f}%")
    
    if best_sharpe_config:
        print(f"\n📊 MEJOR SHARPE RATIO:")
        print(f"   Escenario: {best_sharpe_config[0]}")
        print(f"   Config: {best_sharpe_config[1]}")
        print(f"   Retorno: {best_sharpe_config[2]['return_pct']:.2f}%")
        print(f"   Sharpe: {best_sharpe_config[2]['sharpe_ratio']:.2f}")
        print(f"   Drawdown: {best_sharpe_config[2]['max_drawdown']:.2f}%")
    
    # Resumen por configuración
    print("\n" + "="*100)
    print("📋 RESUMEN POR CONFIGURACIÓN (promedio de todos los escenarios)")
    print("="*100)
    
    config_averages = {}
    for scenario, results in all_results.items():
        for config_name, metrics in results.items():
            if config_name not in config_averages:
                config_averages[config_name] = {'returns': [], 'sharpes': [], 'drawdowns': []}
            config_averages[config_name]['returns'].append(metrics['return_pct'])
            config_averages[config_name]['sharpes'].append(metrics['sharpe_ratio'])
            config_averages[config_name]['drawdowns'].append(metrics['max_drawdown'])
    
    print(f"\n{'Configuración':<25} {'Retorno Prom':>12} {'Sharpe Prom':>12} {'DD Prom':>12}")
    print("-" * 65)
    for config_name, avgs in config_averages.items():
        avg_return = sum(avgs['returns']) / len(avgs['returns'])
        avg_sharpe = sum(avgs['sharpes']) / len(avgs['sharpes'])
        avg_dd = sum(avgs['drawdowns']) / len(avgs['drawdowns'])
        print(f"{config_name:<25} {avg_return:>11.2f}% {avg_sharpe:>12.2f} {avg_dd:>11.2f}%")
    
    print("\n" + "="*100)
    print("Pruebas completadas con datos reales de Binance")
    print("="*100)


if __name__ == '__main__':
    main()
