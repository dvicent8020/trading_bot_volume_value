"""
Script de análisis de rendimiento de operaciones.

Analiza las operaciones del backtest para identificar patrones y problemas
en la estrategia, especialmente relacionados con stops y cierres de posición.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from trading_bot.backtester import Backtester
from trading_bot.data_handler import DataHandler
from trading_bot.volume_value_strategy import VolumeValueStrategy
from test_volume_value_strategy import get_risk_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_trades(trades_df: pd.DataFrame, symbol: str, timeframe: str) -> dict:
    """
    Analiza las operaciones y genera estadísticas detalladas.
    
    Args:
        trades_df: DataFrame con operaciones de get_trades()
        symbol: Símbolo del par (ej: 'BTC/USDT')
        timeframe: Timeframe usado (ej: '4h', '1d')
        
    Returns:
        Diccionario con estadísticas de análisis
    """
    if trades_df.empty:
        return {
            'total_trades': 0,
            'error': 'No hay operaciones para analizar'
        }
    
    # Estadísticas generales
    total_trades = len(trades_df)
    winning_trades = trades_df[trades_df['P&L (%)'] > 0]
    losing_trades = trades_df[trades_df['P&L (%)'] <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    
    # Análisis por razón de cierre
    exit_reason_stats = {}
    if 'Exit Reason' in trades_df.columns:
        for reason in trades_df['Exit Reason'].unique():
            reason_trades = trades_df[trades_df['Exit Reason'] == reason]
            reason_wins = reason_trades[reason_trades['P&L (%)'] > 0]
            
            exit_reason_stats[reason] = {
                'count': len(reason_trades),
                'win_rate': len(reason_wins) / len(reason_trades) if len(reason_trades) > 0 else 0.0,
                'avg_pnl_pct': reason_trades['P&L (%)'].mean(),
                'total_pnl_pct': reason_trades['P&L (%)'].sum(),
                'avg_pnl_usd': reason_trades['P&L ($)'].mean(),
                'total_pnl_usd': reason_trades['P&L ($)'].sum(),
                'max_win': reason_trades['P&L (%)'].max(),
                'max_loss': reason_trades['P&L (%)'].min(),
            }
    
    # Comparar tamaño promedio de ganancias vs pérdidas
    avg_win_size = winning_trades['P&L (%)'].mean() if len(winning_trades) > 0 else 0.0
    avg_loss_size = abs(losing_trades['P&L (%)'].mean()) if len(losing_trades) > 0 else 0.0
    win_loss_ratio = avg_win_size / avg_loss_size if avg_loss_size > 0 else 0.0
    
    # Análisis de riesgo/recompensa
    total_wins_pct = winning_trades['P&L (%)'].sum() if len(winning_trades) > 0 else 0.0
    total_losses_pct = abs(losing_trades['P&L (%)'].sum()) if len(losing_trades) > 0 else 0.0
    profit_factor = total_wins_pct / total_losses_pct if total_losses_pct > 0 else 0.0
    
    # Análisis por tipo de operación
    long_trades = trades_df[trades_df['Tipo'] == 'LONG']
    short_trades = trades_df[trades_df['Tipo'] == 'SHORT']
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'avg_win_size_pct': avg_win_size,
        'avg_loss_size_pct': avg_loss_size,
        'win_loss_ratio': win_loss_ratio,
        'profit_factor': profit_factor,
        'total_return_pct': trades_df['P&L (%)'].sum(),
        'exit_reason_stats': exit_reason_stats,
        'long_trades': {
            'count': len(long_trades),
            'win_rate': len(long_trades[long_trades['P&L (%)'] > 0]) / len(long_trades) if len(long_trades) > 0 else 0.0,
            'avg_pnl_pct': long_trades['P&L (%)'].mean() if len(long_trades) > 0 else 0.0,
        },
        'short_trades': {
            'count': len(short_trades),
            'win_rate': len(short_trades[short_trades['P&L (%)'] > 0]) / len(short_trades) if len(short_trades) > 0 else 0.0,
            'avg_pnl_pct': short_trades['P&L (%)'].mean() if len(short_trades) > 0 else 0.0,
        }
    }


def print_analysis_report(analysis: dict):
    """
    Imprime un reporte de análisis formateado.
    """
    if 'error' in analysis:
        logger.error(f"Error: {analysis['error']}")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"ANÁLISIS DE RENDIMIENTO: {analysis['symbol']} - {analysis['timeframe']}")
    logger.info(f"{'='*80}\n")
    
    logger.info(f"📊 ESTADÍSTICAS GENERALES:")
    logger.info(f"  • Total de operaciones: {analysis['total_trades']}")
    logger.info(f"  • Win Rate: {analysis['win_rate']*100:.2f}%")
    logger.info(f"  • Operaciones ganadoras: {analysis['winning_trades']}")
    logger.info(f"  • Operaciones perdedoras: {analysis['losing_trades']}")
    logger.info(f"  • Retorno Total: {analysis['total_return_pct']:.2f}%")
    logger.info(f"  • Profit Factor: {analysis['profit_factor']:.2f}")
    
    logger.info(f"\n💰 TAMAÑO DE OPERACIONES:")
    logger.info(f"  • Ganancias promedio: {analysis['avg_win_size_pct']:.2f}%")
    logger.info(f"  • Pérdidas promedio: {analysis['avg_loss_size_pct']:.2f}%")
    logger.info(f"  • Ratio Win/Loss: {analysis['win_loss_ratio']:.2f}")
    
    if analysis['win_loss_ratio'] < 1.0:
        logger.warning(f"  ⚠️ Las ganancias promedio son MENORES que las pérdidas promedio!")
        logger.warning(f"  Esto significa que necesitas un win rate >{100/(1+analysis['win_loss_ratio']):.1f}% para ser rentable")
    
    logger.info(f"\n📈 ANÁLISIS POR TIPO:")
    logger.info(f"  LONG:")
    logger.info(f"    • Operaciones: {analysis['long_trades']['count']}")
    logger.info(f"    • Win Rate: {analysis['long_trades']['win_rate']*100:.2f}%")
    logger.info(f"    • P&L Promedio: {analysis['long_trades']['avg_pnl_pct']:.2f}%")
    logger.info(f"  SHORT:")
    logger.info(f"    • Operaciones: {analysis['short_trades']['count']}")
    logger.info(f"    • Win Rate: {analysis['short_trades']['win_rate']*100:.2f}%")
    logger.info(f"    • P&L Promedio: {analysis['short_trades']['avg_pnl_pct']:.2f}%")
    
    if analysis['exit_reason_stats']:
        logger.info(f"\n🎯 ANÁLISIS POR RAZÓN DE CIERRE:")
        for reason, stats in analysis['exit_reason_stats'].items():
            logger.info(f"  {reason}:")
            logger.info(f"    • Cantidad: {stats['count']} ({stats['count']/analysis['total_trades']*100:.1f}%)")
            logger.info(f"    • Win Rate: {stats['win_rate']*100:.2f}%")
            logger.info(f"    • P&L Promedio: {stats['avg_pnl_pct']:.2f}%")
            logger.info(f"    • P&L Total: {stats['total_pnl_pct']:.2f}%")
            logger.info(f"    • Mayor Ganancia: {stats['max_win']:.2f}%")
            logger.info(f"    • Mayor Pérdida: {stats['max_loss']:.2f}%")
    
    logger.info(f"\n{'='*80}\n")


def main():
    """Ejecuta análisis para un par y timeframe específico."""
    symbol = 'BTC/USDT'
    timeframe = '1d'
    days = 365
    
    logger.info(f"Analizando {symbol} - {timeframe} - {days} días")
    
    # Obtener datos (futures para usar leverage)
    data_handler = DataHandler(symbol, market_type='futures')
    data = data_handler.fetch_historical_data(timeframe, days=days)
    
    if data.empty:
        logger.error("No se pudieron obtener datos")
        return
    
    # Configurar estrategia
    risk_config = get_risk_config(symbol)
    strategy = VolumeValueStrategy(
        market_regime_enabled=risk_config.get('market_regime_enabled', False),
        adx_period=risk_config.get('adx_period', 14),
        adx_threshold=risk_config.get('adx_threshold', 30.0)
    )
    
    # Generar señales
    signals = strategy.generate_signals(data)
    
    # Configurar backtester
    backtester = Backtester(
        initial_capital=5000.0,
        commission=0.001,
        market_type='futures',
        leverage=risk_config.get('leverage', 1.0),
        trailing_stop_activation=risk_config.get('trailing_stop_activation'),
        trailing_stop_distance=risk_config.get('trailing_stop_distance'),
        stop_loss_pct=risk_config.get('stop_loss_pct'),
        atr_period=risk_config.get('atr_period'),
        atr_multiplier=risk_config.get('atr_multiplier'),
        tp_dynamic_enabled=risk_config.get('tp_dynamic_enabled', False),
        tp_partial_pct=risk_config.get('tp_partial_pct'),
        tp_atr_multiplier=risk_config.get('tp_atr_multiplier'),
        tp_vwap_band=risk_config.get('tp_vwap_band'),
        strategy_instance=strategy
    )
    
    # Ejecutar backtest
    results = backtester.run_backtest(data, signals)
    
    # Obtener operaciones
    trades_df = backtester.get_trades(results)
    
    # Analizar operaciones
    analysis = analyze_trades(trades_df, symbol, timeframe)
    
    # Imprimir reporte
    print_analysis_report(analysis)
    
    # Guardar operaciones en CSV para análisis adicional
    output_file = f"trades_analysis_{symbol.replace('/', '_')}_{timeframe}.csv"
    trades_df.to_csv(output_file, index=False)
    logger.info(f"Operaciones guardadas en: {output_file}")


if __name__ == '__main__':
    main()
