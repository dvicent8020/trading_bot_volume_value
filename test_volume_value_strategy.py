#!/usr/bin/env python3
"""
Script para probar VolumeValueStrategy en múltiples pares.
Timeframe: 4h, Período: 90 días
"""

import logging
import sys
from datetime import datetime
from trading_bot import VolumeValueStrategy, DataHandler, Backtester
from trading_bot.exceptions import TradingBotError

def setup_logging(log_level: str = 'INFO'):
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def get_risk_config(symbol: str, timeframe: str = '1d', leverage_mode: str = 'conservador'):
    """
    Retorna configuración de riesgo optimizada.
    
    BTC/USDT: Configuración optimizada basada en análisis del 2026-01-15
    
    Modos de leverage disponibles:
    - 'conservador': 3x leverage, mejor balance riesgo/retorno (Sharpe 2.01, DD -28%)
    - 'balanceado': 5x leverage, mayor retorno con más riesgo (Sharpe 2.01, DD -74%)
    - 'agresivo': 5x/10x leverage según timeframe
    
    Para 4H solo SHORTs: 10x es viable (100% win rate, Sharpe 3.40)
    
    Altcoins: Configuración conservadora
    """
    if symbol == 'BTC/USDT':
        # Configuraciones base por modo de leverage
        if timeframe == '4h':
            # En 4H solo SHORTs funcionan (100% win rate), podemos usar más leverage
            configs = {
                'conservador': {'lev': 3.0, 'sl': 0.05, 'ta': 0.03, 'td': 0.01},
                'balanceado': {'lev': 5.0, 'sl': 0.05, 'ta': 0.03, 'td': 0.01},
                'agresivo': {'lev': 10.0, 'sl': 0.02, 'ta': 0.02, 'td': 0.005},
            }
        else:  # 1d
            configs = {
                'conservador': {'lev': 3.0, 'sl': 0.05, 'ta': 0.03, 'td': 0.01},
                'balanceado': {'lev': 5.0, 'sl': 0.05, 'ta': 0.03, 'td': 0.01},
                'agresivo': {'lev': 5.0, 'sl': 0.06, 'ta': 0.03, 'td': 0.008},
            }
        
        cfg = configs.get(leverage_mode, configs['conservador'])
        
        return {
            'leverage': cfg['lev'],
            'trailing_stop_activation': cfg['ta'],
            'trailing_stop_distance': cfg['td'],
            'stop_loss_pct': cfg['sl'],
            'take_profit_pct': 0.15,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 20.0,
            'signal_cooldown': 3,
            # Nuevos filtros de mejora
            'disable_longs': timeframe == '4h',  # Deshabilitar LONGs en 4H (0% win rate)
            'disable_shorts': False,
            'require_uptrend_for_longs': True,
            'trend_filter_period': 50,
            # TP Parcial
            'tp_dynamic_enabled': False,
            'tp_partial_pct': None,
            'tp_atr_multiplier': None,
            'tp_vwap_band': None
        }
    else:  # ETH, SOL, XRP
        return {
            'leverage': 3.0,
            'trailing_stop_activation': 0.03,
            'trailing_stop_distance': 0.012,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.12,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 20.0,
            'signal_cooldown': 3,
            'disable_longs': False,
            'disable_shorts': False,
            'require_uptrend_for_longs': False,
            'trend_filter_period': 50,
            'tp_dynamic_enabled': False,
            'tp_partial_pct': None,
            'tp_atr_multiplier': None,
            'tp_vwap_band': None
        }

def run_test(symbol: str, timeframe: str, days: int = None, start_date: datetime = None, end_date: datetime = None):
    """Ejecuta un backtest con VolumeValueStrategy y gestión de riesgo cuantitativa."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PRUEBA VOLUME VALUE STRATEGY - {symbol}")
    if start_date and end_date:
        logger.info(f"Timeframe: {timeframe}, Período: {start_date.date()} - {end_date.date()}")
    else:
        logger.info(f"Timeframe: {timeframe}, Período: {days} días")
    logger.info(f"{'='*80}")
    
    try:
        market_type = 'futures'
        initial_capital = 5000.0
        commission = 0.001
        
        # Obtener configuración de riesgo según activo y timeframe
        risk_config = get_risk_config(symbol, timeframe)
        logger.info(f"\n📊 CONFIGURACIÓN DE RIESGO PARA {symbol}:")
        logger.info(f"  • Leverage: {risk_config['leverage']}x")
        logger.info(f"  • Trailing Stop Activation: {risk_config['trailing_stop_activation']*100:.2f}%")
        logger.info(f"  • Trailing Stop Distance: {risk_config['trailing_stop_distance']*100:.2f}%")
        if risk_config['stop_loss_pct'] is not None:
            logger.info(f"  • Hard Stop Loss: {risk_config['stop_loss_pct']*100:.2f}%")
        else:
            logger.info(f"  • Hard Stop Loss: None (solo ATR dinámico)")
        logger.info(f"  • ATR Filter: {'Activado' if risk_config['use_atr'] else 'Desactivado'} (Period={risk_config['atr_period']}, Multiplier={risk_config['atr_multiplier']})")
        logger.info(f"  • ADX Market Regime Filter: {'Activado' if risk_config['market_regime_enabled'] else 'Desactivado'} (Threshold={risk_config['adx_threshold']})")
        # Mostrar nuevos filtros
        if risk_config.get('disable_longs'):
            logger.info(f"  • LONGs: DESHABILITADOS (para este timeframe)")
        if risk_config.get('require_uptrend_for_longs'):
            logger.info(f"  • Filtro Tendencia Mayor: LONGs solo si precio > SMA{risk_config.get('trend_filter_period', 50)}")
        
        # Descargar datos
        data_handler = DataHandler(symbol=symbol, market_type=market_type)
        
        # Si se especifican fechas, descargar más datos y filtrar
        if start_date and end_date:
            # Calcular días totales desde start_date hasta ahora para descargar
            total_days = (datetime.now() - start_date).days + 365
            data = data_handler.fetch_historical_data(timeframe=timeframe, days=total_days)
            # Filtrar por rango de fechas
            data = data[(data.index >= start_date) & (data.index <= end_date)]
            logger.info(f"Datos filtrados para período: {start_date.date()} - {end_date.date()}")
        else:
            data = data_handler.fetch_historical_data(timeframe=timeframe, days=days)
        
        data_handler.validate_data(data)
        
        logger.info(f"\nDatos: {len(data)} velas")
        logger.info(f"Precio inicial: ${data['close'].iloc[0]:,.2f}")
        logger.info(f"Precio final: ${data['close'].iloc[-1]:,.2f}")
        
        # Configuración VolumeValueStrategy con filtros de riesgo cuantitativo
        # Ajustar período de VWAP según timeframe (7 días para 1D = semanal)
        vwap_period = 7 if timeframe == '1D' else 7
        strategy = VolumeValueStrategy(
            vwap_period_days=vwap_period,  # VWAP semanal
            volume_profile_period=7,  # Volume Profile semanal
            value_area_percent=0.68,  # 68% estándar AMT
            delta_lookback=20,  # Período para CVD
            volatility_threshold=3.0,  # 300% del promedio
            min_volume_period=20,  # Período para promedio de volumen
            lvn_lookback=50,  # Período para detectar LVN
            market_regime_enabled=risk_config['market_regime_enabled'],  # Filtro ADX
            adx_period=risk_config['adx_period'],
            adx_threshold=risk_config['adx_threshold'],
            # Configuración simplificada
            signal_cooldown=risk_config.get('signal_cooldown', 3),
            # Filtros deshabilitados
            min_signal_strength=0.0,
            volume_confirmation_enabled=False,
            long_filters_enabled=False,
            # Nuevos filtros de mejora
            disable_longs=risk_config.get('disable_longs', False),
            disable_shorts=risk_config.get('disable_shorts', False),
            require_uptrend_for_longs=risk_config.get('require_uptrend_for_longs', False),
            trend_filter_period=risk_config.get('trend_filter_period', 50)
        )
        
        # generate_signals detecta automáticamente el timeframe del índice de datos
        signals = strategy.generate_signals(data)
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_signals = buy_signals + sell_signals
        
        logger.info(f"\nSeñales generadas: {buy_signals} LONG, {sell_signals} SHORT (Total: {total_signals})")
        
        if total_signals == 0:
            logger.warning("⚠️ No se generaron señales para este par")
            return None
        
        # Backtest con gestión de riesgo cuantitativa
        # ATR actúa como stop dinámico principal (Filtro A)
        # stop_loss_pct actúa como hard stop de emergencia (última línea de defensa)
        # El Backtester ahora permite ambos: usa el más conservador (el más cercano al precio)
        backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            stop_loss_pct=risk_config['stop_loss_pct'],  # Hard stop de emergencia
            take_profit_pct=0.08,
            market_type=market_type,
            leverage=risk_config['leverage'],
            trailing_stop_activation=risk_config['trailing_stop_activation'],
            trailing_stop_distance=risk_config['trailing_stop_distance'],
            atr_period=risk_config['atr_period'] if risk_config['use_atr'] else None,
            atr_multiplier=risk_config['atr_multiplier'] if risk_config['use_atr'] else None,
            # Scaling Out (Salidas Parciales)
            tp_dynamic_enabled=risk_config.get('tp_dynamic_enabled', False),
            tp_partial_pct=risk_config.get('tp_partial_pct'),
            tp_atr_multiplier=risk_config.get('tp_atr_multiplier'),
            tp_vwap_band=risk_config.get('tp_vwap_band'),
            strategy_instance=strategy  # Pasar instancia de estrategia para calcular bandas VWAP
        )
        
        results = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, timeframe=timeframe)
        
        retorno = metrics.get('total_return_pct', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        drawdown = metrics.get('max_drawdown_pct', 0)
        final_capital = metrics.get('final_capital', initial_capital)
        win_rate = metrics.get('win_rate', 0)
        num_trades = metrics.get('num_trades', 0)
        
        # Calcular porcentaje semanal
        # Si hay datos, calcular semanas desde datos reales
        if len(data) > 0:
            period_days = (data.index[-1] - data.index[0]).days
            weeks = max(period_days / 7, 1)  # Mínimo 1 semana
        else:
            weeks = days / 7 if days else 52  # Fallback a 1 año
        
        total_profit = final_capital - initial_capital
        weekly_profit = total_profit / weeks if weeks > 0 else 0
        weekly_percentage = (weekly_profit / initial_capital) * 100 if initial_capital > 0 else 0
        
        logger.info(f"\n{'='*80}")
        logger.info("RESULTADOS:")
        logger.info(f"{'='*80}")
        logger.info(f"  • Señales: {total_signals} ({buy_signals} LONG, {sell_signals} SHORT)")
        logger.info(f"  • Operaciones: {num_trades}")
        logger.info(f"  • Win Rate: {win_rate*100:.2f}%")
        logger.info(f"  • Retorno Total: {retorno:.2f}%")
        logger.info(f"  • Sharpe Ratio: {sharpe:.2f}")
        logger.info(f"  • Maximum Drawdown: {drawdown:.2f}%")
        logger.info(f"  • Capital Final: ${final_capital:,.2f}")
        logger.info(f"  • Ganancia Total: ${final_capital - initial_capital:,.2f}")
        logger.info(f"  • Ganancia Semanal: ${weekly_profit:,.2f}")
        logger.info(f"  • Porcentaje Semanal: {weekly_percentage:.2f}%")
        
        # Verificar objetivos
        logger.info(f"\n  Objetivos:")
        logger.info(f"    • Mínimo: 5%/semana = $250/semana")
        logger.info(f"    • Ideal: 8%/semana = $400/semana")
        
        if weekly_percentage >= 8.0:
            logger.info(f"\n  ✅✅ CUMPLE OBJETIVO IDEAL (8% semanal)")
        elif weekly_percentage >= 5.0:
            logger.info(f"\n  ✅ CUMPLE OBJETIVO MÍNIMO (5% semanal)")
        else:
            logger.warning(f"\n  ⚠️ NO alcanza objetivo mínimo (falta {5.0 - weekly_percentage:.2f}%)")
        
        # Verificar liquidación
        has_liquidation = drawdown <= -99.0
        if has_liquidation:
            logger.error(f"\n  ❌ LIQUIDACIÓN DETECTADA")
        
        return {
            'symbol': symbol,
            'signals': total_signals,
            'trades': num_trades,
            'win_rate': win_rate,
            'retorno': retorno,
            'sharpe': sharpe,
            'drawdown': drawdown,
            'final_capital': final_capital,
            'weekly_percentage': weekly_percentage,
            'has_liquidation': has_liquidation
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando prueba para {symbol}: {e}", exc_info=True)
        return None

def main():
    """Función principal."""
    setup_logging('INFO')
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("PRUEBAS SCALING OUT - MULTIPLE CONFIGURACIONES")
    logger.info("="*80)
    
    pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
    
    # Configuraciones de prueba
    test_configs = [
        {'timeframe': '4h', 'days': 90, 'description': '4H - 90 días'},
        {'timeframe': '1d', 'days': 90, 'description': '1D - 90 días'},
        {'timeframe': '4h', 'days': 365, 'description': '4H - 365 días'},
        {'timeframe': '1d', 'days': 365, 'description': '1D - 365 días'},
        {'timeframe': '4h', 'year': 2022, 'description': '4H - Solo 2022'},
        {'timeframe': '1d', 'year': 2022, 'description': '1D - Solo 2022'}
    ]
    
    all_results = []
    
    for config in test_configs:
        timeframe = config['timeframe']
        description = config['description']
        
        logger.info(f"\n\n{'='*80}")
        logger.info(f"CONFIGURACIÓN: {description}")
        logger.info(f"Scaling Out: Activado (TP Parcial: BTC 40%, Altcoins 60%)")
        logger.info(f"{'='*80}\n")
        
        if 'year' in config:
            # Para 2022, usar fechas específicas
            start_2022 = datetime(2022, 1, 1)
            end_2022 = datetime(2022, 12, 31, 23, 59, 59)
            start_date = start_2022
            end_date = end_2022
            days = None
        else:
            days = config['days']
            start_date = None
            end_date = None
        
        for pair in pairs:
            logger.info(f"\n{'-'*80}")
            logger.info(f"Probando {pair} - {description}")
            logger.info(f"{'-'*80}")
            
            try:
                result = run_test(pair, timeframe, days=days, start_date=start_date, end_date=end_date)
                
                if result:
                    all_results.append({
                        'Configuración': description,
                        'Par': result['symbol'],
                        'Señales': result['signals'],
                        'Operaciones': result['trades'],
                        'Win Rate %': f"{result['win_rate']*100:.2f}%",
                        'Retorno %': f"{result['retorno']:.2f}%",
                        'Sharpe': f"{result['sharpe']:.2f}",
                        'Drawdown %': f"{result['drawdown']:.2f}%",
                        '%/Semana': f"{result['weekly_percentage']:.2f}%",
                        'Liquidación': 'Sí' if result['has_liquidation'] else 'No'
                    })
            except Exception as e:
                logger.error(f"Error en prueba {pair} - {description}: {e}", exc_info=True)
    
    # Resumen comparativo final
    if all_results:
        logger.info(f"\n\n{'='*80}")
        logger.info("RESUMEN COMPARATIVO FINAL - SCALING OUT")
        logger.info(f"{'='*80}")
        
        # Agrupar por configuración
        for config_desc in [c['description'] for c in test_configs]:
            config_results = [r for r in all_results if r['Configuración'] == config_desc]
            if config_results:
                logger.info(f"\n\n{config_desc}:")
                logger.info(f"{'Par':<12} {'Señales':<10} {'Ops':<6} {'Win Rate':<10} {'Retorno %':<12} {'Sharpe':<8} {'Drawdown %':<12} {'%/Semana':<12} {'Liquidación':<12}")
                logger.info("-" * 110)
                
                for r in config_results:
                    logger.info(
                        f"{r['Par']:<12} {r['Señales']:<10} {r['Operaciones']:<6} {r['Win Rate %']:<10} "
                        f"{r['Retorno %']:<12} {r['Sharpe']:<8} {r['Drawdown %']:<12} {r['%/Semana']:<12} {r['Liquidación']:<12}"
                    )
        
        # Estadísticas globales
        logger.info(f"\n\n{'='*80}")
        logger.info("ESTADÍSTICAS GLOBALES:")
        logger.info(f"{'='*80}")
        
        total_tests = len(all_results)
        total_liquidations = sum(1 for r in all_results if r['Liquidación'] == 'Sí')
        objectives_met = sum(1 for r in all_results if float(r['%/Semana'].replace('%', '')) >= 5.0)
        
        logger.info(f"  • Total de pruebas: {total_tests}")
        logger.info(f"  • Liquidaciones: {total_liquidations} ({total_liquidations/total_tests*100:.1f}%)")
        logger.info(f"  • Objetivos cumplidos (≥5%/semana): {objectives_met} ({objectives_met/total_tests*100:.1f}%)")
        
        # Mejores resultados por métrica
        if all_results:
            best_return = max(all_results, key=lambda x: float(x['Retorno %'].replace('%', '').replace(' (Liquidación)', '')))
            best_sharpe = max(all_results, key=lambda x: float(x['Sharpe']))
            
            non_liquidated = [r for r in all_results if r['Liquidación'] == 'No']
            if non_liquidated:
                lowest_drawdown = min(non_liquidated, key=lambda x: abs(float(x['Drawdown %'].replace('%', ''))))
            else:
                lowest_drawdown = min(all_results, key=lambda x: abs(float(x['Drawdown %'].replace('%', '').replace(' (Liquidación)', ''))))
            
            logger.info(f"\n  📈 MEJORES RESULTADOS:")
            logger.info(f"     • Mejor Retorno: {best_return['Par']} - {best_return['Configuración']} ({best_return['Retorno %']})")
            logger.info(f"     • Mejor Sharpe: {best_sharpe['Par']} - {best_sharpe['Configuración']} ({best_sharpe['Sharpe']})")
            logger.info(f"     • Menor Drawdown: {lowest_drawdown['Par']} - {lowest_drawdown['Configuración']} ({lowest_drawdown['Drawdown %']})")
        
        # Resumen de configuración aplicada
        logger.info(f"\n{'='*80}")
        logger.info("CONFIGURACIÓN DE SCALING OUT:")
        logger.info(f"{'='*80}")
        logger.info("  BTC/USDT:")
        logger.info("    • Leverage: 10x | Trailing Stop: 1.5%/0.8% | Hard Stop: 4%")
        logger.info("    • TP Parcial: 40% | TP VWAP Band: 3.0 desviaciones estándar")
        logger.info("    • ATR Filter: ON (14, 1.5x) | ADX Filter: ON (Threshold: 30.0)")
        logger.info("  Altcoins (ETH, SOL, XRP):")
        logger.info("    • Leverage: 3x | Trailing Stop: 2.0%/1.0% | Hard Stop: 4%")
        logger.info("    • TP Parcial: 60% | TP ATR Multiplier: 2.5x")
        logger.info("    • ATR Filter: ON (14, 1.5x) | ADX Filter: ON (Threshold: 30.0)")

if __name__ == "__main__":
    main()
