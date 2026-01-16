#!/usr/bin/env python3
"""
Script para probar configuraciones más agresivas y aumentar frecuencia de operaciones.
Objetivo: $500-1000 semanales ($5000 capital inicial)
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

def test_aggressive_config(symbol: str, timeframe: str, days: int):
    """Prueba configuración agresiva para más operaciones."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"CONFIGURACIÓN AGRESIVA - {symbol}")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info(f"{'='*80}")
    
    try:
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        logger.info(f"\nDatos: {len(data)} velas")
        logger.info(f"Precio inicial: ${data['close'].iloc[0]:,.2f}")
        logger.info(f"Precio final: ${data['close'].iloc[-1]:,.2f}")
        
        # Configuraciones a probar (de menos a más agresiva)
        configs = [
            {
                'name': 'Configuración Actual (Optimizada)',
                'ema_period': 200,
                'rsi_oversold': 30.0,
                'rsi_overbought': 70.0,
                'volume_ratio_threshold': 1.0,
                'delta_confirmation_candles': 2
            },
            {
                'name': 'Más Flexible (RSI 35/65, VR 0.8, Delta 1)',
                'ema_period': 200,
                'rsi_oversold': 35.0,
                'rsi_overbought': 65.0,
                'volume_ratio_threshold': 0.8,
                'delta_confirmation_candles': 1
            },
            {
                'name': 'Muy Agresiva (RSI 40/60, VR 0.7, Delta 1)',
                'ema_period': 200,
                'rsi_oversold': 40.0,
                'rsi_overbought': 60.0,
                'volume_ratio_threshold': 0.7,
                'delta_confirmation_candles': 1
            },
            {
                'name': 'Ultra Agresiva (RSI 45/55, VR 0.6, Delta 1, EMA 100)',
                'ema_period': 100,  # EMA más corta para más señales
                'rsi_oversold': 45.0,
                'rsi_overbought': 55.0,
                'volume_ratio_threshold': 0.6,
                'delta_confirmation_candles': 1
            }
        ]
        
        best_config = None
        best_return = -float('inf')
        best_signals = 0
        
        for config in configs:
            logger.info(f"\n{'='*80}")
            logger.info(f"Probando: {config['name']}")
            logger.info(f"{'='*80}")
            
            # Ajustar EMA period si timeframe es muy corto
            ema_period = config['ema_period']
            if timeframe == '1h' and len(data) < ema_period:
                ema_period = min(100, len(data) - 20)
                logger.info(f"  Ajustando EMA a {ema_period} para timeframe 1h")
            
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
            buy_signals = (signals == 1).sum()
            sell_signals = (signals == -1).sum()
            total_signals = buy_signals + sell_signals
            
            logger.info(f"Señales: {buy_signals} LONG, {sell_signals} SHORT (Total: {total_signals})")
            
            if total_signals == 0:
                logger.warning("  Sin señales generadas")
                continue
            
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
            
            retorno = metrics.get('total_return_pct', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            drawdown = metrics.get('max_drawdown_pct', 0)
            final_capital = metrics.get('final_capital', initial_capital)
            
            # Calcular ganancia semanal
            weeks = days / 7
            weekly_profit = (final_capital - initial_capital) / weeks
            
            logger.info(f"\nResultados:")
            logger.info(f"  Retorno Total: {retorno:.2f}%")
            logger.info(f"  Sharpe Ratio: {sharpe:.2f}")
            logger.info(f"  Drawdown: {drawdown:.2f}%")
            logger.info(f"  Capital Final: ${final_capital:,.2f}")
            logger.info(f"  Ganancia Total: ${final_capital - initial_capital:,.2f}")
            logger.info(f"  Ganancia Semanal: ${weekly_profit:,.2f}")
            logger.info(f"  Objetivo mínimo: $500/semana")
            logger.info(f"  Objetivo ideal: $1,000/semana")
            
            # Verificar si cumple objetivos
            if weekly_profit >= 500:
                status = "✅ CUMPLE OBJETIVO MÍNIMO" if weekly_profit < 1000 else "✅✅ CUMPLE OBJETIVO IDEAL"
                logger.info(f"  {status}")
            
            # Guardar mejor configuración
            if retorno > best_return:
                best_return = retorno
                best_signals = total_signals
                best_config = {
                    **config,
                    'ema_period': ema_period,
                    'retorno': retorno,
                    'signals': total_signals,
                    'sharpe': sharpe,
                    'drawdown': drawdown,
                    'weekly_profit': weekly_profit,
                    'final_capital': final_capital
                }
        
        # Resumen
        if best_config:
            logger.info(f"\n{'='*80}")
            logger.info("MEJOR CONFIGURACIÓN ENCONTRADA")
            logger.info(f"{'='*80}")
            logger.info(f"Nombre: {best_config['name']}")
            logger.info(f"Parámetros:")
            logger.info(f"  • EMA Period: {best_config['ema_period']}")
            logger.info(f"  • RSI: {best_config['rsi_oversold']}/{best_config['rsi_overbought']}")
            logger.info(f"  • Volume Ratio Threshold: {best_config['volume_ratio_threshold']}")
            logger.info(f"  • Delta Confirmation Candles: {best_config['delta_confirmation_candles']}")
            logger.info(f"\nResultados:")
            logger.info(f"  • Señales: {best_config['signals']}")
            logger.info(f"  • Retorno: {best_config['retorno']:.2f}%")
            logger.info(f"  • Sharpe: {best_config['sharpe']:.2f}")
            logger.info(f"  • Drawdown: {best_config['drawdown']:.2f}%")
            logger.info(f"  • Ganancia Semanal: ${best_config['weekly_profit']:,.2f}")
            logger.info(f"  • Capital Final: ${best_config['final_capital']:,.2f}")
            
            if best_config['weekly_profit'] >= 1000:
                logger.info(f"\n✅✅ Esta configuración CUMPLE el objetivo IDEAL ($1,000/semana)")
            elif best_config['weekly_profit'] >= 500:
                logger.info(f"\n✅ Esta configuración CUMPLE el objetivo MÍNIMO ($500/semana)")
            else:
                logger.warning(f"\n⚠️ Esta configuración NO alcanza el objetivo mínimo")
                logger.info(f"   Necesita: ${500 - best_config['weekly_profit']:,.2f} más por semana")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    # Probar diferentes configuraciones
    pairs = ['XRP/USDT', 'ETH/USDT', 'BTC/USDT']
    timeframes = ['4h', '1h']  # Probar 1h para más señales
    
    logger.info("="*80)
    logger.info("PRUEBAS CON CONFIGURACIONES AGRESIVAS")
    logger.info("Objetivo: $500-1,000 semanales ($5,000 capital inicial)")
    logger.info("="*80)
    
    for timeframe in timeframes:
        for pair in pairs:
            logger.info(f"\n\n{'#'*80}")
            logger.info(f"# TIMEFRAME: {timeframe} | PAR: {pair} | 90 DÍAS")
            logger.info(f"{'#'*80}")
            test_aggressive_config(pair, timeframe, 90)

if __name__ == "__main__":
    main()
