#!/usr/bin/env python3
"""
Script para optimizar parámetros por par de trading.
Ajusta ATR multiplier y leverage para reducir liquidaciones.
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

def test_configuration(symbol: str, timeframe: str, days: int, 
                       atr_multiplier: float, leverage: float):
    """Prueba una configuración específica."""
    logger = logging.getLogger(__name__)
    
    try:
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        # Crear estrategia
        strategy = FunnelStrategy(
            ema_period=200,
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            volume_period=20,
            volume_ratio_threshold=1.0,
            delta_confirmation_candles=2,
            delta_lookback=3
        )
        
        # Generar señales
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
            leverage=leverage,
            trailing_stop_activation=0.05,
            trailing_stop_distance=0.02,
            atr_period=14,
            atr_multiplier=atr_multiplier
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        # Verificar si hubo liquidación
        liquidation = metrics.get('max_drawdown_pct', 0) <= -99.0
        
        return {
            'symbol': symbol,
            'atr_multiplier': atr_multiplier,
            'leverage': leverage,
            'signals': total_signals,
            'return_pct': metrics.get('total_return_pct', 0),
            'sharpe': metrics.get('sharpe_ratio', 0),
            'drawdown': metrics.get('max_drawdown_pct', 0),
            'liquidation': liquidation,
            'final_capital': metrics.get('final_capital', 5000)
        }
        
    except Exception as e:
        logger.debug(f"Error: {e}")
        return None

def optimize_pair(symbol: str, timeframe: str = '4h', days: int = 90):
    """Optimiza parámetros para un par específico."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"OPTIMIZACIÓN: {symbol} - {timeframe}, {days} días")
    logger.info(f"{'='*80}")
    
    # Configuraciones a probar
    atr_multipliers = [1.5, 2.0, 2.5, 3.0]
    leverages = [5.0, 7.5, 10.0]
    
    results = []
    
    for atr_mult in atr_multipliers:
        for lev in leverages:
            print(f"  Probando: ATR={atr_mult}x, Leverage={lev}x...", end=' ', flush=True)
            
            result = test_configuration(symbol, timeframe, days, atr_mult, lev)
            
            if result and not result['liquidation']:
                print(f"✓ Retorno: {result['return_pct']:.2f}%, Drawdown: {result['drawdown']:.2f}%")
                results.append(result)
            elif result and result['liquidation']:
                print(f"✗ Liquidación detectada")
            else:
                print(f"- Sin señales")
    
    if not results:
        logger.warning(f"\n⚠ No se encontraron configuraciones sin liquidación para {symbol}")
        return None
    
    # Ordenar por Sharpe Ratio (mejor balance riesgo/retorno)
    results.sort(key=lambda x: x['sharpe'], reverse=True)
    
    best = results[0]
    
    logger.info(f"\n{'='*80}")
    logger.info(f"MEJOR CONFIGURACIÓN PARA {symbol}:")
    logger.info(f"{'='*80}")
    logger.info(f"  ATR Multiplier: {best['atr_multiplier']}x")
    logger.info(f"  Leverage: {best['leverage']}x")
    logger.info(f"  Señales: {best['signals']}")
    logger.info(f"  Retorno: {best['return_pct']:.2f}%")
    logger.info(f"  Sharpe Ratio: {best['sharpe']:.2f}")
    logger.info(f"  Maximum Drawdown: {best['drawdown']:.2f}%")
    logger.info(f"  Capital Final: ${best['final_capital']:,.2f}")
    
    return best

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    pairs = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT']
    timeframe = '4h'
    days = 90
    
    logger.info("="*80)
    logger.info("OPTIMIZACIÓN DE PARÁMETROS POR PAR")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info("="*80)
    
    optimized_configs = {}
    
    for pair in pairs:
        best_config = optimize_pair(pair, timeframe, days)
        if best_config:
            optimized_configs[pair] = best_config
    
    # Resumen final
    if optimized_configs:
        logger.info(f"\n{'='*80}")
        logger.info("RESUMEN DE CONFIGURACIONES ÓPTIMAS")
        logger.info(f"{'='*80}")
        logger.info(f"{'Par':<12} {'ATR':<6} {'Leverage':<10} {'Retorno %':<12} {'Sharpe':<8} {'Drawdown %':<12}")
        logger.info("-" * 80)
        
        for pair, config in optimized_configs.items():
            logger.info(
                f"{pair:<12} {config['atr_multiplier']:<6} {config['leverage']:<10.1f} "
                f"{config['return_pct']:>10.2f}%  {config['sharpe']:>6.2f}  "
                f"{config['drawdown']:>10.2f}%"
            )

if __name__ == "__main__":
    main()
