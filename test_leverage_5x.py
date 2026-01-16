#!/usr/bin/env python3
"""
Script de prueba para FunnelStrategy con leverage 5x.
Prueba todos los pares con configuración óptima pero leverage reducido.
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

def test_pair_leverage_5x(symbol: str, timeframe: str = '4h', days: int = 90, atr_multiplier: float = 1.5):
    """Prueba la estrategia con leverage 5x."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PRUEBA CON LEVERAGE 5X - {symbol}")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info(f"{'='*80}")
    
    try:
        # Configuración
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        leverage = 5.0  # Leverage reducido
        
        logger.info(f"\nConfiguración:")
        logger.info(f"  - Símbolo: {symbol}")
        logger.info(f"  - Leverage: {leverage}x (reducido)")
        logger.info(f"  - ATR Multiplier: {atr_multiplier}x")
        logger.info(f"  - Capital inicial: ${initial_capital:,.2f}")
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        logger.info(f"  - Datos: {len(data)} velas")
        logger.info(f"  - Precio inicial: ${data['close'].iloc[0]:,.2f}")
        logger.info(f"  - Precio final: ${data['close'].iloc[-1]:,.2f}")
        
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
        
        logger.info(f"\nSeñales generadas:")
        logger.info(f"  - LONG: {buy_signals}, SHORT: {sell_signals}, Total: {total_signals}")
        
        if total_signals == 0:
            logger.warning("No se generaron señales")
            return {
                'symbol': symbol,
                'leverage': leverage,
                'atr_multiplier': atr_multiplier,
                'signals': 0,
                'error': 'Sin señales'
            }
        
        # Backtest con leverage 5x
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
        
        # Verificar liquidación
        liquidation = metrics.get('max_drawdown_pct', 0) <= -99.0
        
        logger.info(f"\n{'='*80}")
        logger.info("RESULTADOS:")
        logger.info(f"{'='*80}")
        logger.info(f"  Retorno Total: {metrics.get('total_return_pct', 0):.2f}%")
        logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        logger.info(f"  Maximum Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
        logger.info(f"  Capital Final: ${metrics.get('final_capital', 5000):,.2f}")
        logger.info(f"  Liquidación: {'Sí' if liquidation else 'No'}")
        
        return {
            'symbol': symbol,
            'leverage': leverage,
            'atr_multiplier': atr_multiplier,
            'signals': total_signals,
            'return_pct': metrics.get('total_return_pct', 0),
            'sharpe': metrics.get('sharpe_ratio', 0),
            'drawdown': metrics.get('max_drawdown_pct', 0),
            'final_capital': metrics.get('final_capital', 5000),
            'liquidation': liquidation,
            'win_rate': metrics.get('win_rate', 0),
            'total_trades': metrics.get('total_trades', 0)
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            'symbol': symbol,
            'leverage': leverage,
            'error': str(e)
        }

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    # Pares a probar con sus configuraciones óptimas de ATR
    pairs_config = [
        ('BTC/USDT', 1.5),
        ('ETH/USDT', 1.5),
        ('XRP/USDT', 2.0),  # Mayor volatilidad
        ('SOL/USDT', 1.5),
    ]
    
    timeframe = '4h'
    days = 90
    
    logger.info("="*80)
    logger.info("PRUEBAS CON LEVERAGE 5X - FUNNEL STRATEGY")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info("="*80)
    
    results = []
    
    for symbol, atr_mult in pairs_config:
        result = test_pair_leverage_5x(symbol, timeframe, days, atr_mult)
        if result and 'error' not in result:
            results.append(result)
    
    # Resumen comparativo
    if results:
        logger.info("\n" + "="*80)
        logger.info("RESUMEN COMPARATIVO - LEVERAGE 5X")
        logger.info("="*80)
        logger.info(f"{'Par':<12} {'ATR':<6} {'Señales':<10} {'Retorno %':<12} {'Sharpe':<10} {'Drawdown %':<12} {'Liquidación':<12}")
        logger.info("-" * 90)
        
        for result in results:
            symbol = result['symbol']
            atr = result['atr_multiplier']
            signals = result['signals']
            retorno = result['return_pct']
            sharpe = result['sharpe']
            drawdown = result['drawdown']
            liq = 'Sí' if result['liquidation'] else 'No'
            
            logger.info(
                f"{symbol:<12} {atr:<6} {signals:<10} {retorno:>10.2f}%  {sharpe:>8.2f}  "
                f"{drawdown:>10.2f}%  {liq:<12}"
            )
        
        logger.info("\n" + "="*80)
        logger.info("COMPARACIÓN LEVERAGE 5X vs 10X")
        logger.info("="*80)
        logger.info("\nNota: Comparar estos resultados con las pruebas anteriores con leverage 10x")
        logger.info("para evaluar el impacto del leverage reducido en retornos y riesgo.")

if __name__ == "__main__":
    main()
