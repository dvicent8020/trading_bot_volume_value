#!/usr/bin/env python3
"""
Script para probar configuraciones que alcancen 5-8% semanal.
Objetivo: Retorno semanal del 5-8% del capital inicial.
"""

import logging
import sys
from trading_bot import FunnelStrategy, DataHandler, Backtester
from trading_bot.exceptions import TradingBotError

def setup_logging(log_level: str = 'INFO'):
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_config_for_weekly_percentage(symbol: str, timeframe: str, days: int, config: dict):
    """Prueba una configuración para alcanzar 5-8% semanal."""
    logger = logging.getLogger(__name__)
    
    try:
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        # Ajustar EMA si es necesario
        ema_period = config['ema_period']
        if timeframe == '1h' and len(data) < ema_period:
            ema_period = min(100, len(data) - 20)
        
        strategy = FunnelStrategy(
            ema_period=ema_period,
            rsi_period=14,
            rsi_oversold=config['rsi_oversold'],
            rsi_overbought=config['rsi_overbought'],
            volume_period=20,
            volume_ratio_threshold=config['volume_ratio_threshold'],
            delta_confirmation_candles=config['delta_confirmation_candles'],
            delta_lookback=3
        )
        
        signals = strategy.generate_signals(data)
        total_signals = (signals != 0).sum()
        
        if total_signals == 0:
            return None
        
        # Backtest
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=None,
            take_profit_pct=0.08,
            market_type=market_type,
            leverage=config.get('leverage', 10.0),
            trailing_stop_activation=0.05,
            trailing_stop_distance=0.02,
            atr_period=14,
            atr_multiplier=config.get('atr_multiplier', 1.5)
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        retorno = metrics.get('total_return_pct', 0)
        final_capital = metrics.get('final_capital', initial_capital)
        sharpe = metrics.get('sharpe_ratio', 0)
        drawdown = metrics.get('max_drawdown_pct', 0)
        
        # Calcular porcentaje semanal
        weeks = days / 7
        weekly_profit = final_capital - initial_capital
        weekly_percentage = (weekly_profit / weeks) / initial_capital * 100
        
        # Verificar si cumple objetivos
        meets_5pct = weekly_percentage >= 5.0
        meets_8pct = weekly_percentage >= 8.0
        liquidation = drawdown <= -99.0
        
        return {
            'config_name': config['name'],
            'symbol': symbol,
            'timeframe': timeframe,
            'signals': total_signals,
            'retorno_pct': retorno,
            'weekly_percentage': weekly_percentage,
            'sharpe': sharpe,
            'drawdown': drawdown,
            'final_capital': final_capital,
            'meets_5pct': meets_5pct,
            'meets_8pct': meets_8pct,
            'liquidation': liquidation
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("PRUEBAS PARA ALCANZAR 5-8% SEMANAL")
    logger.info("="*80)
    
    # Configuraciones a probar
    configs = [
        {
            'name': 'Balanceada (4h)',
            'ema_period': 200,
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'volume_ratio_threshold': 1.0,
            'delta_confirmation_candles': 2,
            'leverage': 10.0,
            'atr_multiplier': 1.5
        },
        {
            'name': 'Más Flexible (4h)',
            'ema_period': 200,
            'rsi_oversold': 35.0,
            'rsi_overbought': 65.0,
            'volume_ratio_threshold': 0.8,
            'delta_confirmation_candles': 1,
            'leverage': 10.0,
            'atr_multiplier': 2.0
        },
        {
            'name': 'Agresiva Balanceada (4h)',
            'ema_period': 200,
            'rsi_oversold': 40.0,
            'rsi_overbought': 60.0,
            'volume_ratio_threshold': 0.7,
            'delta_confirmation_candles': 1,
            'leverage': 8.0,  # Leverage reducido
            'atr_multiplier': 2.5  # Más protección
        },
        {
            'name': 'Timeframe 1h Balanceada',
            'ema_period': 100,
            'rsi_oversold': 35.0,
            'rsi_overbought': 65.0,
            'volume_ratio_threshold': 0.8,
            'delta_confirmation_candles': 1,
            'leverage': 8.0,
            'atr_multiplier': 2.5
        }
    ]
    
    pairs = ['XRP/USDT', 'ETH/USDT', 'BTC/USDT']
    timeframes = ['4h', '1h']
    
    all_results = []
    
    for timeframe in timeframes:
        for pair in pairs:
            logger.info(f"\n{'='*80}")
            logger.info(f"Probando: {pair} - {timeframe}")
            logger.info(f"{'='*80}")
            
            for config in configs:
                if timeframe == '1h' and '1h' not in config['name']:
                    continue
                if timeframe == '4h' and '1h' in config['name']:
                    continue
                
                result = test_config_for_weekly_percentage(pair, timeframe, 90, config)
                
                if result:
                    all_results.append(result)
                    
                    status = ""
                    if result['liquidation']:
                        status = "❌ LIQUIDACIÓN"
                    elif result['meets_8pct']:
                        status = "✅✅ CUMPLE 8%"
                    elif result['meets_5pct']:
                        status = "✅ CUMPLE 5%"
                    else:
                        status = "⚠️ NO CUMPLE"
                    
                    logger.info(
                        f"  {config['name']}: "
                        f"{result['signals']} señales, "
                        f"{result['weekly_percentage']:.2f}%/semana, "
                        f"Retorno: {result['retorno_pct']:.2f}%, "
                        f"Drawdown: {result['drawdown']:.2f}% "
                        f"{status}"
                    )
    
    # Resumen de mejores configuraciones
    if all_results:
        logger.info(f"\n{'='*80}")
        logger.info("MEJORES CONFIGURACIONES (5-8% semanal)")
        logger.info(f"{'='*80}")
        
        # Filtrar sin liquidaciones y que cumplan 5%
        valid_results = [r for r in all_results if not r['liquidation'] and r['meets_5pct']]
        
        if valid_results:
            # Ordenar por porcentaje semanal
            valid_results.sort(key=lambda x: x['weekly_percentage'], reverse=True)
            
            logger.info(f"\n{'Par':<12} {'Timeframe':<10} {'Config':<25} {'Señales':<8} {'%/Semana':<10} {'Retorno %':<12} {'Drawdown %':<12}")
            logger.info("-" * 100)
            
            for result in valid_results[:10]:  # Top 10
                logger.info(
                    f"{result['symbol']:<12} {result['timeframe']:<10} "
                    f"{result['config_name']:<25} {result['signals']:<8} "
                    f"{result['weekly_percentage']:>8.2f}%  {result['retorno_pct']:>10.2f}%  "
                    f"{result['drawdown']:>10.2f}%"
                )
        else:
            logger.warning("\n⚠️ No se encontraron configuraciones que cumplan 5% semanal sin liquidaciones")
            logger.info("Considerar:")
            logger.info("  • Aumentar capital inicial")
            logger.info("  • Operar múltiples pares simultáneamente")
            logger.info("  • Ajustar objetivos a 3-5% semanal")

if __name__ == "__main__":
    main()
