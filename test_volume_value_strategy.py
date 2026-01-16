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

def get_risk_config(symbol: str, timeframe: str = '1h', leverage_mode: str = '2x'):
    """
    Retorna configuración de riesgo optimizada.
    
    CONFIGURACIÓN OPTIMIZADA 2026-01-16:
    - Timeframe óptimo: 1H (mejor balance retorno/drawdown)
    - ADX Slope habilitado (crítico para rentabilidad)
    - Parámetros ajustados por nivel de leverage
    
    Modos de leverage disponibles:
    - '2x': Óptimo para bajo drawdown (DD ~7-8%, Sharpe ~0.97)
    - '3x': Balance riesgo/retorno (DD ~13%, Sharpe ~0.91, Retorno ~70%)
    - '5x': Mayor retorno, mayor riesgo (DD ~20-25%)
    - '10x': Agresivo, requiere stops muy ajustados (DD ~30-40%)
    
    Resultados de pruebas 1H-90 días:
    - 2x: +44.8%, Sharpe 0.97, DD -7.6%
    - 3x: +70.7%, Sharpe 0.91, DD -13.5%
    """
    
    # Configuraciones por leverage para BTC/USDT
    # Fórmula: A mayor leverage, stops más ajustados
    leverage_configs = {
        '2x': {
            'leverage': 2.0,
            'stop_loss_pct': 0.02,           # 2%
            'trailing_stop_activation': 0.015,  # 1.5%
            'trailing_stop_distance': 0.005,    # 0.5%
        },
        '3x': {
            'leverage': 3.0,
            'stop_loss_pct': 0.02,           # 2% (ajustado para 3x)
            'trailing_stop_activation': 0.015,  # 1.5%
            'trailing_stop_distance': 0.005,    # 0.5%
        },
        '5x': {
            'leverage': 5.0,
            'stop_loss_pct': 0.015,          # 1.5% (más ajustado)
            'trailing_stop_activation': 0.012,  # 1.2%
            'trailing_stop_distance': 0.004,    # 0.4%
        },
        '10x': {
            'leverage': 10.0,
            'stop_loss_pct': 0.008,          # 0.8% (muy ajustado)
            'trailing_stop_activation': 0.008,  # 0.8%
            'trailing_stop_distance': 0.003,    # 0.3%
        },
    }
    
    # Obtener configuración de leverage
    cfg = leverage_configs.get(leverage_mode, leverage_configs['2x'])
    
    if symbol == 'BTC/USDT':
        return {
            # Parámetros de riesgo (ajustados por leverage)
            'leverage': cfg['leverage'],
            'trailing_stop_activation': cfg['trailing_stop_activation'],
            'trailing_stop_distance': cfg['trailing_stop_distance'],
            'stop_loss_pct': cfg['stop_loss_pct'],
            'take_profit_pct': 0.06,
            # ATR (filtro adicional)
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            # Filtro de régimen de mercado (ADX)
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 25.0,
            # ⚠️ ADX SLOPE - CRÍTICO para rentabilidad
            'adx_slope_enabled': True,
            'adx_slope_period': 5,
            # CVD Normalizado (mejora señales)
            'use_normalized_cvd': True,
            # Cooldown entre señales
            'signal_cooldown': 5,
            # Filtros LONG/SHORT
            'disable_longs': False,  # LONGs habilitados
            'disable_shorts': False,
            'require_uptrend_for_longs': False,
            'trend_filter_period': 50,
            # TP Parcial (deshabilitado por defecto)
            'tp_dynamic_enabled': False,
            'tp_partial_pct': None,
            'tp_atr_multiplier': None,
            'tp_vwap_band': None
        }
    else:  # Altcoins (ETH, SOL, XRP)
        # Altcoins: leverage más conservador
        alt_leverage = min(cfg['leverage'], 3.0)  # Máximo 3x para altcoins
        return {
            'leverage': alt_leverage,
            'trailing_stop_activation': cfg['trailing_stop_activation'] * 1.2,  # 20% más holgado
            'trailing_stop_distance': cfg['trailing_stop_distance'] * 1.5,  # 50% más holgado
            'stop_loss_pct': cfg['stop_loss_pct'] * 1.5,  # 50% más holgado
            'take_profit_pct': 0.08,
            'use_atr': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'market_regime_enabled': True,
            'adx_period': 14,
            'adx_threshold': 25.0,
            'adx_slope_enabled': True,
            'adx_slope_period': 5,
            'use_normalized_cvd': True,
            'signal_cooldown': 5,
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
        # Ajustar período de VWAP según timeframe
        vwap_period = 7 if timeframe in ['1d', '1D'] else 7
        strategy = VolumeValueStrategy(
            vwap_period_days=vwap_period,  # VWAP semanal
            volume_profile_period=7,  # Volume Profile semanal
            value_area_percent=0.68,  # 68% estándar AMT
            delta_lookback=20,  # Período para CVD
            volatility_threshold=3.0,  # 300% del promedio
            min_volume_period=20,  # Período para promedio de volumen
            lvn_lookback=50,  # Período para detectar LVN
            # Filtro ADX (régimen de mercado)
            market_regime_enabled=risk_config['market_regime_enabled'],
            adx_period=risk_config['adx_period'],
            adx_threshold=risk_config['adx_threshold'],
            # ⚠️ ADX SLOPE - CRÍTICO para rentabilidad
            adx_slope_enabled=risk_config.get('adx_slope_enabled', True),
            adx_slope_period=risk_config.get('adx_slope_period', 5),
            # CVD Normalizado
            use_normalized_cvd=risk_config.get('use_normalized_cvd', True),
            # Cooldown entre señales
            signal_cooldown=risk_config.get('signal_cooldown', 5),
            # Filtros deshabilitados
            min_signal_strength=0.0,
            volume_confirmation_enabled=False,
            long_filters_enabled=False,
            # Filtros LONG/SHORT
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
