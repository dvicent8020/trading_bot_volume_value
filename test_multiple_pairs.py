#!/usr/bin/env python3
"""
Script de prueba para FunnelStrategy con múltiples pares de trading.
Prueba ETH/USDT y XRP/USDT en timeframe 4h, 90 días.
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

def test_pair(symbol: str, timeframe: str = '4h', days: int = 90):
    """Prueba la estrategia con un par específico."""
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info(f"PRUEBA DE FUNNEL STRATEGY - {symbol}")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info("="*80)
    
    try:
        # Configuración
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        logger.info(f"\nConfiguración:")
        logger.info(f"  - Símbolo: {symbol}")
        logger.info(f"  - Tipo de Mercado: {market_type.upper()}")
        logger.info(f"  - Timeframe: {timeframe}")
        logger.info(f"  - Días históricos: {days}")
        logger.info(f"  - Capital inicial: ${initial_capital:,.2f}")
        logger.info(f"  - Comisión: {commission*100}%")
        
        # Parámetros de la estrategia Funnel Logic (configuración óptima)
        logger.info(f"\nParámetros de Funnel Strategy (Configuración Óptima):")
        logger.info(f"  - EMA Period: 200")
        logger.info(f"  - RSI Period: 14")
        logger.info(f"  - RSI Oversold: 30.0")
        logger.info(f"  - RSI Overbought: 70.0")
        logger.info(f"  - Volume Period: 20")
        logger.info(f"  - Volume Ratio Threshold: 1.0")
        logger.info(f"  - Delta Confirmation Candles: 2")
        
        # ===== 1. DESCARGAR DATOS =====
        logger.info(f"\n{'='*80}")
        logger.info("PASO 1: Descargando datos históricos")
        logger.info(f"{'='*80}")
        
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        data_handler.validate_data(data)
        
        logger.info(f"Datos descargados: {len(data)} velas")
        logger.info(f"Período: {data.index[0]} a {data.index[-1]}")
        logger.info(f"Precio inicial: ${data['close'].iloc[0]:,.2f}")
        logger.info(f"Precio final: ${data['close'].iloc[-1]:,.2f}")
        
        # ===== 2. CONFIGURAR ESTRATEGIA =====
        logger.info(f"\n{'='*80}")
        logger.info("PASO 2: Configurando Funnel Strategy")
        logger.info(f"{'='*80}")
        
        strategy = FunnelStrategy(
            ema_period=200,
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            volume_period=20,
            volume_ratio_threshold=1.0,
            delta_confirmation_candles=2,  # Configuración óptima
            delta_lookback=3
        )
        
        logger.info(f"Parámetros de la estrategia: {strategy.get_params()}")
        
        # ===== 3. GENERAR SEÑALES =====
        logger.info(f"\n{'='*80}")
        logger.info("PASO 3: Generando señales con Funnel Logic")
        logger.info(f"{'='*80}")
        
        signals = strategy.generate_signals(data)
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_signals = buy_signals + sell_signals
        
        logger.info(f"Señales generadas:")
        logger.info(f"  - Señales LONG (compra): {buy_signals}")
        logger.info(f"  - Señales SHORT (venta): {sell_signals}")
        logger.info(f"  - Total de señales: {total_signals}")
        
        if total_signals == 0:
            logger.warning("No se generaron señales. Esto puede ser normal con Funnel Logic.")
            logger.info("La estrategia es muy selectiva y requiere condiciones específicas.")
            return None
        
        # ===== 4. EJECUTAR BACKTEST =====
        logger.info(f"\n{'='*80}")
        logger.info("PASO 4: Ejecutando backtest")
        logger.info(f"{'='*80}")
        
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=None,  # Usar ATR
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
        trades = backtester.get_trades(results)
        
        # ===== 5. MOSTRAR RESULTADOS =====
        logger.info(f"\n{'='*80}")
        logger.info("RESULTADOS DEL BACKTEST")
        logger.info(f"{'='*80}")
        backtester.print_summary(metrics)
        
        logger.info(f"\n{'='*80}")
        logger.info("DETALLE DE OPERACIONES")
        logger.info(f"{'='*80}")
        backtester.print_trades(trades)
        
        return {
            'symbol': symbol,
            'metrics': metrics,
            'trades': trades,
            'signals_count': total_signals
        }
        
    except TradingBotError as e:
        logger.error(f"Error del sistema de trading: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        return None

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    # Pares a probar
    pairs = ['ETH/USDT', 'XRP/USDT']
    timeframe = '4h'
    days = 90
    
    logger.info("="*80)
    logger.info("PRUEBA MÚLTIPLE PARES - FUNNEL STRATEGY")
    logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info("="*80)
    
    results = []
    
    for pair in pairs:
        try:
            result = test_pair(pair, timeframe=timeframe, days=days)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error probando {pair}: {e}")
            continue
        
        logger.info("\n" + "="*80 + "\n")
    
    # Resumen comparativo
    if results:
        logger.info("="*80)
        logger.info("RESUMEN COMPARATIVO")
        logger.info("="*80)
        logger.info(f"{'Par':<12} {'Señales':<10} {'Retorno %':<12} {'Sharpe':<10} {'Drawdown %':<12}")
        logger.info("-" * 80)
        
        for result in results:
            symbol = result['symbol']
            metrics = result['metrics']
            signals = result['signals_count']
            retorno = metrics.get('total_return_pct', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            drawdown = metrics.get('max_drawdown_pct', 0)
            
            logger.info(f"{symbol:<12} {signals:<10} {retorno:>10.2f}%  {sharpe:>8.2f}  {drawdown:>10.2f}%")
        
        logger.info("="*80)

if __name__ == "__main__":
    main()
