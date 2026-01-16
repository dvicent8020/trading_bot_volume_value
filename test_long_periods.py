#!/usr/bin/env python3
"""
Script de prueba para FunnelStrategy con períodos más largos (180 y 365 días).
Valida la consistencia de la estrategia en diferentes pares.
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

def test_pair_period(symbol: str, timeframe: str, days: int):
    """Prueba la estrategia con un par y período específico."""
    logger = logging.getLogger(__name__)
    
    try:
        # Configuración
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        # Crear estrategia (configuración óptima)
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
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_signals = buy_signals + sell_signals
        
        if total_signals == 0:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'days': days,
                'signals': 0,
                'error': 'Sin señales'
            }
        
        # Backtest
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=None,
            take_profit_pct=0.08,
            market_type=market_type,
            leverage=10.0,
            trailing_stop_activation=0.05,
            trailing_stop_distance=0.02,
            atr_period=14,
            atr_multiplier=1.5
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'days': days,
            'signals': total_signals,
            'metrics': metrics,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error probando {symbol} ({timeframe}, {days}d): {e}")
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'days': days,
            'signals': 0,
            'error': str(e)
        }

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    # Configuración
    pairs = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT']
    timeframe = '4h'
    periods = [180, 365]
    
    logger.info("="*80)
    logger.info("PRUEBAS CON PERÍODOS LARGOS - FUNNEL STRATEGY")
    logger.info(f"Timeframe: {timeframe}")
    logger.info("="*80)
    
    all_results = []
    
    for pair in pairs:
        logger.info(f"\n{'='*80}")
        logger.info(f"Probando {pair}")
        logger.info(f"{'='*80}")
        
        for days in periods:
            logger.info(f"\nPeríodo: {days} días")
            result = test_pair_period(pair, timeframe, days)
            all_results.append(result)
            
            if result['error']:
                logger.warning(f"  ❌ {result['error']}")
            elif result['signals'] == 0:
                logger.warning(f"  ⚠ Sin señales generadas")
            else:
                metrics = result['metrics']
                logger.info(f"  ✓ Señales: {result['signals']}")
                logger.info(f"    Retorno: {metrics.get('total_return_pct', 0):.2f}%")
                logger.info(f"    Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
                logger.info(f"    Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
    
    # Resumen comparativo
    logger.info("\n" + "="*80)
    logger.info("RESUMEN COMPARATIVO - PERÍODOS LARGOS")
    logger.info("="*80)
    
    # Agrupar por período
    for days in periods:
        logger.info(f"\n{'='*80}")
        logger.info(f"PERÍODO: {days} DÍAS")
        logger.info(f"{'='*80}")
        logger.info(f"{'Par':<12} {'Señales':<10} {'Retorno %':<12} {'Sharpe':<10} {'Drawdown %':<12}")
        logger.info("-" * 80)
        
        period_results = [r for r in all_results if r['days'] == days and not r['error'] and r['signals'] > 0]
        
        for result in period_results:
            symbol = result['symbol']
            metrics = result['metrics']
            signals = result['signals']
            retorno = metrics.get('total_return_pct', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            drawdown = metrics.get('max_drawdown_pct', 0)
            
            logger.info(f"{symbol:<12} {signals:<10} {retorno:>10.2f}%  {sharpe:>8.2f}  {drawdown:>10.2f}%")
        
        if not period_results:
            logger.info("  (Sin resultados disponibles)")

if __name__ == "__main__":
    main()
