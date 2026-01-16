"""
Script principal para ejecutar el backtesting del bot de trading.

Este script descarga datos históricos de BTC/USDT, ejecuta una estrategia
de cruce de medias móviles y muestra los resultados del backtest.
"""

import logging
import sys
from datetime import datetime
from trading_bot import DataHandler, SMACrossover, Backtester
from trading_bot.exceptions import TradingBotError


def setup_logging(log_level: str = 'INFO'):
    """
    Configura el sistema de logging.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Función principal del script."""
    # Configurar logging
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("INICIANDO BACKTEST DE TRADING BOT")
    logger.info("="*60)
    
    try:
        # ===== CONFIGURACIÓN =====
        symbol = 'BTC/USDT'
        market_type = 'futures'  # 'spot' o 'futures' - Cambiar aquí para alternar
        timeframe = '4h'  # Timeframe mejorado para más operaciones
        days = 365  # 1 año de datos
        initial_capital = 5000.0
        commission = 0.001  # 0.1%
        
        # Parámetros de la estrategia mejorados para timeframe 4h
        fast_period = 15   # Períodos optimizados para más señales
        slow_period = 40   # Períodos optimizados para mayor estabilidad
        rsi_period = 14    # RSI activado para filtrar operaciones
        rsi_overbought = 75.0  # RSI más restrictivo para compras
        rsi_oversold = 25.0    # RSI más restrictivo para ventas
        trend_filter_period = 100  # Filtro de tendencia (SMA larga)
        
        # Parámetros de riesgo
        stop_loss_pct = 0.015   # Stop loss del 1.5%
        take_profit_pct = 0.08  # Take profit del 8%
        trailing_stop_activation = 0.05  # Activar trailing stop cuando ganancia > 5%
        trailing_stop_distance = 0.02  # Trailing stop a 2% del precio máximo
        leverage = 10.0 if market_type == 'futures' else 1.0  # Leverage 10x para futuros, 1x para spot
        
        logger.info(f"Configuración:")
        logger.info(f"  - Símbolo: {symbol}")
        logger.info(f"  - Tipo de Mercado: {market_type.upper()}")
        logger.info(f"  - Timeframe: {timeframe}")
        logger.info(f"  - Días históricos: {days}")
        logger.info(f"  - Capital inicial: ${initial_capital:,.2f}")
        logger.info(f"  - Comisión: {commission*100}%")
        logger.info(f"  - Apalancamiento: {leverage}x" if leverage > 1.0 else "  - Apalancamiento: Sin apalancamiento")
        logger.info(f"  - Estrategia: SMA Crossover ({fast_period}/{slow_period})")
        logger.info(f"  - Filtros: RSI({rsi_period}), Trend SMA({trend_filter_period})")
        logger.info(f"  - Riesgo: Stop Loss {stop_loss_pct*100}%, Take Profit {take_profit_pct*100}%")
        
        # ===== 1. DESCARGAR DATOS =====
        logger.info("\n" + "-"*60)
        logger.info("PASO 1: Descargando datos históricos")
        logger.info("-"*60)
        
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
        
        # ===== 2. GENERAR SEÑALES =====
        logger.info("\n" + "-"*60)
        logger.info("PASO 2: Generando señales de la estrategia")
        logger.info("-"*60)
        
        strategy = SMACrossover(
            fast_period=fast_period,
            slow_period=slow_period,
            rsi_period=rsi_period,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
            trend_filter_period=trend_filter_period
        )
        signals = strategy.generate_signals(data)
        
        logger.info(f"Parámetros de la estrategia: {strategy.get_params()}")
        
        # ===== 3. EJECUTAR BACKTEST =====
        logger.info("\n" + "-"*60)
        logger.info("PASO 3: Ejecutando backtest")
        logger.info("-"*60)
        
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            market_type=market_type,
            leverage=leverage,
            trailing_stop_activation=trailing_stop_activation,
            trailing_stop_distance=trailing_stop_distance
        )
        results = backtester.run_backtest(data, signals)
        
        # ===== 4. CALCULAR Y MOSTRAR MÉTRICAS =====
        logger.info("\n" + "-"*60)
        logger.info("PASO 4: Calculando métricas de rendimiento")
        logger.info("-"*60)
        
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        backtester.print_summary(metrics)
        
        # ===== 5. MOSTRAR OPERACIONES =====
        logger.info("\n" + "-"*60)
        logger.info("PASO 5: Extrayendo operaciones realizadas")
        logger.info("-"*60)
        
        trades = backtester.get_trades(results)
        backtester.print_trades(trades)
        
        logger.info("Backtest completado exitosamente")
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
    sys.exit(main())
