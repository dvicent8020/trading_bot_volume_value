#!/usr/bin/env python3
"""
Script para optimizar configuraciones de altcoins (ETH, SOL, XRP).
Prueba múltiples combinaciones para reducir drawdown y mantener ganancias aceptables.
"""

import logging
import sys
from trading_bot import VolumeValueStrategy, DataHandler, Backtester
from trading_bot.exceptions import TradingBotError

def setup_logging(log_level: str = 'INFO'):
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def run_test_config(symbol: str, timeframe: str, days: int, config_name: str, config: dict):
    """Ejecuta un backtest con una configuración específica."""
    logger = logging.getLogger(__name__)
    
    try:
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        # Configuración VolumeValueStrategy
        strategy = VolumeValueStrategy(
            vwap_period_days=7,
            volume_profile_period=7,
            value_area_percent=0.68,
            delta_lookback=20,
            volatility_threshold=3.0,
            min_volume_period=20,
            lvn_lookback=50,
            market_regime_enabled=config['market_regime_enabled'],
            adx_period=config['adx_period'],
            adx_threshold=config['adx_threshold']
        )
        
        signals = strategy.generate_signals(data)
        total_signals = (signals != 0).sum()
        
        if total_signals == 0:
            return None
        
        # Backtest
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=config['stop_loss_pct'],
            take_profit_pct=0.08,
            market_type=market_type,
            leverage=config['leverage'],
            trailing_stop_activation=config['trailing_stop_activation'],
            trailing_stop_distance=config['trailing_stop_distance'],
            atr_period=config['atr_period'] if config['use_atr'] else None,
            atr_multiplier=config['atr_multiplier'] if config['use_atr'] else None
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        retorno = metrics.get('total_return_pct', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        drawdown = metrics.get('max_drawdown_pct', 0)
        final_capital = metrics.get('final_capital', initial_capital)
        win_rate = metrics.get('win_rate', 0)
        num_trades = metrics.get('num_trades', 0)
        
        return {
            'config_name': config_name,
            'symbol': symbol,
            'signals': total_signals,
            'trades': num_trades,
            'win_rate': win_rate,
            'retorno': retorno,
            'sharpe': sharpe,
            'drawdown': drawdown,
            'final_capital': final_capital,
            'has_liquidation': drawdown <= -99.0
        }
        
    except Exception as e:
        logger.error(f"Error en {config_name} para {symbol}: {e}")
        return None

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("OPTIMIZACIÓN DE ALTCOINS - VolumeValueStrategy")
    logger.info("Timeframe: 4h | Período: 90 días")
    logger.info("="*80)
    
    pairs = ['ETH/USDT', 'SOL/USDT', 'XRP/USDT']
    timeframe = '4h'
    days = 90
    
    # Definir configuraciones a probar
    configurations = {
        'Config 1 - Conservadora Base': {
            'leverage': 5.0,
            'trailing_stop_activation': 0.02,
            'trailing_stop_distance': 0.015,
            'stop_loss_pct': 0.04,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.8,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 30.0
        },
        'Config 2 - Más Conservadora': {
            'leverage': 4.0,  # Reducido
            'trailing_stop_activation': 0.02,
            'trailing_stop_distance': 0.012,  # Más cercano
            'stop_loss_pct': 0.035,  # Más estricto
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.5,  # Más cercano
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 35.0  # Más selectivo
        },
        'Config 3 - ATR Muy Cercano': {
            'leverage': 5.0,
            'trailing_stop_activation': 0.025,
            'trailing_stop_distance': 0.01,  # Muy agresivo
            'stop_loss_pct': 0.04,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.3,  # Muy cercano
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 30.0
        },
        'Config 4 - Leverage Bajo + ATR Medio': {
            'leverage': 3.0,  # Muy bajo
            'trailing_stop_activation': 0.025,
            'trailing_stop_distance': 0.015,
            'stop_loss_pct': 0.05,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.6,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 30.0
        },
        'Config 5 - ADX Muy Selectivo': {
            'leverage': 5.0,
            'trailing_stop_activation': 0.02,
            'trailing_stop_distance': 0.015,
            'stop_loss_pct': 0.04,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.8,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 40.0  # Muy selectivo
        },
        'Config 6 - Balance Optimizado': {
            'leverage': 4.5,
            'trailing_stop_activation': 0.022,
            'trailing_stop_distance': 0.013,
            'stop_loss_pct': 0.038,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.6,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 32.0
        }
    }
    
    all_results = []
    
    for pair in pairs:
        logger.info(f"\n{'='*80}")
        logger.info(f"PROBANDO CONFIGURACIONES PARA {pair}")
        logger.info(f"{'='*80}")
        
        for config_name, config in configurations.items():
            logger.info(f"\nProbando: {config_name}")
            result = run_test_config(pair, timeframe, days, config_name, config)
            if result:
                all_results.append(result)
                logger.info(
                    f"  {pair}: Retorno={result['retorno']:.2f}%, "
                    f"DD={result['drawdown']:.2f}%, "
                    f"Sharpe={result['sharpe']:.2f}, "
                    f"Ops={result['trades']}"
                )
    
    # Resumen por configuración
    logger.info(f"\n\n{'='*80}")
    logger.info("RESUMEN POR CONFIGURACIÓN")
    logger.info(f"{'='*80}")
    
    for config_name in configurations.keys():
        config_results = [r for r in all_results if r['config_name'] == config_name]
        if config_results:
            avg_return = sum(r['retorno'] for r in config_results) / len(config_results)
            avg_drawdown = sum(r['drawdown'] for r in config_results) / len(config_results)
            avg_sharpe = sum(r['sharpe'] for r in config_results) / len(config_results)
            liquidations = sum(1 for r in config_results if r['has_liquidation'])
            
            logger.info(f"\n{config_name}:")
            logger.info(f"  Retorno Promedio: {avg_return:.2f}%")
            logger.info(f"  Drawdown Promedio: {avg_drawdown:.2f}%")
            logger.info(f"  Sharpe Promedio: {avg_sharpe:.2f}")
            logger.info(f"  Liquidaciones: {liquidations}/{len(config_results)}")
            
            # Mostrar por par
            for pair in pairs:
                pair_result = next((r for r in config_results if r['symbol'] == pair), None)
                if pair_result:
                    logger.info(
                        f"    {pair}: Ret={pair_result['retorno']:.2f}%, "
                        f"DD={pair_result['drawdown']:.2f}%"
                    )
    
    # Encontrar mejores configuraciones
    logger.info(f"\n\n{'='*80}")
    logger.info("MEJORES CONFIGURACIONES POR OBJETIVO")
    logger.info(f"{'='*80}")
    
    # Mejor drawdown promedio
    config_drawdowns = {}
    for config_name in configurations.keys():
        config_results = [r for r in all_results if r['config_name'] == config_name]
        if config_results:
            avg_dd = sum(r['drawdown'] for r in config_results) / len(config_results)
            config_drawdowns[config_name] = avg_dd
    
    best_dd_config = min(config_drawdowns, key=config_drawdowns.get)
    logger.info(f"\n✅ Menor Drawdown Promedio: {best_dd_config}")
    logger.info(f"   Drawdown: {config_drawdowns[best_dd_config]:.2f}%")
    
    # Mejor retorno promedio (con drawdown razonable < 40%)
    config_returns = {}
    for config_name in configurations.keys():
        config_results = [r for r in all_results if r['config_name'] == config_name]
        if config_results:
            avg_dd = sum(r['drawdown'] for r in config_results) / len(config_results)
            avg_ret = sum(r['retorno'] for r in config_results) / len(config_results)
            if avg_dd > -40:  # Drawdown razonable
                config_returns[config_name] = avg_ret
    
    if config_returns:
        best_ret_config = max(config_returns, key=config_returns.get)
        logger.info(f"\n✅ Mejor Retorno (DD < 40%): {best_ret_config}")
        logger.info(f"   Retorno: {config_returns[best_ret_config]:.2f}%")
    
    # Mejor balance (ratio retorno/drawdown)
    config_ratios = {}
    for config_name in configurations.keys():
        config_results = [r for r in all_results if r['config_name'] == config_name]
        if config_results:
            avg_dd = abs(sum(r['drawdown'] for r in config_results) / len(config_results))
            avg_ret = sum(r['retorno'] for r in config_results) / len(config_results)
            if avg_dd > 0 and avg_ret > 0:
                ratio = avg_ret / avg_dd
                config_ratios[config_name] = ratio
    
    if config_ratios:
        best_ratio_config = max(config_ratios, key=config_ratios.get)
        logger.info(f"\n✅ Mejor Balance (Retorno/Drawdown): {best_ratio_config}")
        logger.info(f"   Ratio: {config_ratios[best_ratio_config]:.2f}")

if __name__ == "__main__":
    main()
