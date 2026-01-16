#!/usr/bin/env python3
"""
Script de prueba para FunnelStrategy en timeframe 4h, 90 días.
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

def main(timeframe: str = '4h', days: int = 90):
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    logger.info("="*70)
    logger.info(f"PRUEBA DE FUNNEL STRATEGY - {timeframe}, {days} días")
    logger.info("="*70)
    
    try:
        # Configuración
        symbol = 'BTC/USDT'
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
        
        # Parámetros de la estrategia Funnel Logic (se ajustarán después según datos)
        logger.info(f"\nParámetros de Funnel Strategy:")
        logger.info(f"  - EMA Period: Ajustado según datos disponibles")
        logger.info(f"  - RSI Period: 14")
        logger.info(f"  - RSI Oversold: 30.0")
        logger.info(f"  - RSI Overbought: 70.0")
        logger.info(f"  - Volume Period: 20")
        logger.info(f"  - Volume Ratio Threshold: 1.0 (ajustado para condiciones de mercado)")
        logger.info(f"  - Delta Confirmation Candles: 2 (configuración óptima para menor drawdown)")
        
        # ===== 1. DESCARGAR DATOS =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 1: Descargando datos históricos")
        logger.info("-"*70)
        
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        data = data_handler.fetch_historical_data(
            timeframe=timeframe,
            days=days
        )
        data_handler.validate_data(data)
        
        logger.info(f"Datos descargados: {len(data)} velas")
        logger.info(f"Período: {data.index[0]} a {data.index[-1]}")
        logger.info(f"Precio inicial: ${data['close'].iloc[0]:,.2f}")
        logger.info(f"Precio final: ${data['close'].iloc[-1]:,.2f}")
        
        # ===== 2. CREAR Y CONFIGURAR ESTRATEGIA =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 2: Configurando Funnel Strategy")
        logger.info("-"*70)
        
        # Ajustar EMA period según timeframe y datos disponibles
        # Para 1D, usar EMA más corta si no hay suficientes datos
        if timeframe == '1d':
            if len(data) >= 200:
                ema_period = 200
            elif len(data) >= 100:
                ema_period = 100  # Usar EMA 100 para timeframe 1D con más datos
            else:
                ema_period = min(60, len(data) - 20)  # Usar máximo 60 o datos disponibles - 20
            logger.info(f"  - Ajustando EMA Period a {ema_period} para timeframe 1D")
        else:
            ema_period = 200
        
        # Usar configuración óptima encontrada (Delta=2 para menor drawdown)
        delta_confirmation = 2  # Configuración óptima para menor drawdown
        
        strategy = FunnelStrategy(
            ema_period=ema_period,
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            volume_period=20,
            volume_ratio_threshold=1.0,  # Ajustado para condiciones de mercado
            delta_confirmation_candles=delta_confirmation,  # Configuración óptima: 2
            delta_lookback=3
        )
        
        logger.info(f"Parámetros de la estrategia: {strategy.get_params()}")
        
        # ===== 3. GENERAR SEÑALES =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 3: Generando señales con Funnel Logic")
        logger.info("-"*70)
        
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
            return 0
        
        # Mostrar índices de señales
        signal_indices = signals[signals != 0].index
        logger.info(f"\nFechas de señales:")
        for idx, signal_value in zip(signal_indices, signals[signal_indices]):
            signal_type = "LONG" if signal_value == 1 else "SHORT"
            price = data.loc[idx, 'close']
            logger.info(f"  - {idx}: {signal_type} @ ${price:,.2f}")
        
        # ===== 4. EJECUTAR BACKTEST =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 4: Ejecutando backtest")
        logger.info("-"*70)
        
        # Ajustar ATR multiplier para que stop loss no exceda 20% con leverage 10x
        # Con leverage 10x, un stop loss de 2% del precio = 20% del capital
        # ATR multiplier más conservador para evitar stops muy amplios
        atr_multiplier = 1.5  # Reducido de 2.0 para stop loss más ajustado
        
        logger.info(f"\nParámetros de Risk Management:")
        logger.info(f"  - Stop Loss: ATR dinámico (14x{atr_multiplier})")
        logger.info(f"  - Take Profit: 8%")
        logger.info(f"  - Leverage: 10x")
        logger.info(f"  - Stop Loss máximo estimado: ~15-20% del capital con leverage 10x")
        
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
            atr_multiplier=atr_multiplier
        )
        
        results = backtester.run_backtest(data, signals)
        
        # ===== 5. CALCULAR Y MOSTRAR MÉTRICAS =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 5: Calculando métricas de rendimiento")
        logger.info("-"*70)
        
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        backtester.print_summary(metrics)
        
        # ===== 6. MOSTRAR OPERACIONES =====
        logger.info("\n" + "-"*70)
        logger.info("PASO 6: Extrayendo operaciones realizadas")
        logger.info("-"*70)
        
        trades = backtester.get_trades(results)
        if len(trades) > 0:
            backtester.print_trades(trades)
        else:
            logger.info("No se ejecutaron operaciones (esto puede ser normal con Funnel Logic)")
        
        logger.info("\n" + "="*70)
        logger.info("PRUEBA COMPLETADA EXITOSAMENTE")
        logger.info("="*70)
        
        return 0
        
    except TradingBotError as e:
        logger.error(f"Error del sistema de trading: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario")
        return 130
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        return 1

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Prueba de Funnel Strategy')
    parser.add_argument('--timeframe', type=str, default='4h', help='Timeframe (4h, 1d)')
    parser.add_argument('--days', type=int, default=90, help='Número de días')
    
    args = parser.parse_args()
    sys.exit(main(timeframe=args.timeframe, days=args.days))
