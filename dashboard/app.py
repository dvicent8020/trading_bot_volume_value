"""
Dashboard web con Plotly Dash para visualización y configuración de backtests.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# URL de la API (ajustar según configuración)
API_URL = "http://localhost:8000"

# Inicializar aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "Trading Bot Dashboard"


# ==================== Layout Principal ====================

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Trading Bot Dashboard", className="text-center mb-4"),
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Tabs(id="main-tabs", value="config-tab", children=[
                dcc.Tab(label="Configuración", value="config-tab", children=[
                    html.Div(id="config-content")
                ]),
                dcc.Tab(label="Backtests", value="backtests-tab", children=[
                    html.Div(id="backtests-content")
                ]),
                dcc.Tab(label="Resultados", value="results-tab", children=[
                    html.Div(id="results-content")
                ]),
                dcc.Tab(label="Operaciones", value="trades-tab", children=[
                    html.Div(id="trades-content")
                ]),
                dcc.Tab(label="Señales", value="signals-tab", children=[
                    html.Div(id="signals-content")
                ]),
            ])
        ])
    ]),
    
    # Store para datos
    dcc.Store(id="selected-backtest-store"),
    dcc.Interval(id="interval-component", interval=5000, n_intervals=0, disabled=True),
    
], fluid=True)


# ==================== Callbacks ====================

@app.callback(
    Output("config-content", "children"),
    Input("main-tabs", "value")
)
def render_config_tab(tab):
    """Renderizar contenido de la pestaña de configuración."""
    if tab != "config-tab":
        return html.Div()
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H3("Configurar Backtest"),
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Nombre del Backtest"),
                            dbc.Input(id="config-name", type="text", placeholder="Backtest 1")
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Par de Trading"),
                            dcc.Dropdown(
                                id="config-symbol",
                                options=[
                                    {"label": "BTC/USDT", "value": "BTC/USDT"},
                                    {"label": "ETH/USDT", "value": "ETH/USDT"},
                                    {"label": "XRP/USDT", "value": "XRP/USDT"},
                                    {"label": "SOL/USDT", "value": "SOL/USDT"}
                                ],
                                value="BTC/USDT",
                                searchable=False
                            )
                        ], md=6),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Tipo de Mercado"),
                            dcc.Dropdown(
                                id="config-market-type",
                                options=[
                                    {"label": "Futures", "value": "futures"},
                                    {"label": "Spot", "value": "spot"}
                                ],
                                value="futures"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Timeframe"),
                            dcc.Dropdown(
                                id="config-timeframe",
                                options=[
                                    {"label": "1h", "value": "1h"},
                                    {"label": "4h", "value": "4h"},
                                    {"label": "1d", "value": "1d"}
                                ],
                                value="4h"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Días"),
                            dbc.Input(id="config-days", type="number", value=365, min=1)
                        ], md=4),
                    ]),
                    html.Hr(),
                    html.H5("Capital y Riesgo"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Capital Inicial"),
                            dbc.Input(id="config-initial-capital", type="number", value=5000.0, step=100)
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Comisión (%)"),
                            dbc.Input(id="config-commission", type="number", value=0.1, step=0.01)
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Leverage"),
                            dbc.Input(id="config-leverage", type="number", value=10.0, step=0.5)
                        ], md=4),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Stop Loss (%) - Solo si NO usa ATR"),
                            dbc.Input(id="config-stop-loss", type="number", value="", placeholder="Dejar vacío si usa ATR", step=0.1)
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Take Profit (%)"),
                            dbc.Input(id="config-take-profit", type="number", value=8.0, step=0.5)
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Trailing Stop Activation (%)"),
                            dbc.Input(id="config-trailing-activation", type="number", value=5.0, step=0.5)
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Trailing Stop Distance (%)"),
                            dbc.Input(id="config-trailing-distance", type="number", value=2.0, step=0.1)
                        ], md=3),
                    ]),
                    html.Hr(),
                    html.H5("Estrategia"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Tipo de Estrategia"),
                            dcc.Dropdown(
                                id="config-strategy-type",
                                options=[
                                    {"label": "SMA Crossover", "value": "SMA_CROSSOVER"},
                                    {"label": "Funnel Logic", "value": "FUNNEL_LOGIC"},
                                    {"label": "Volume Value Strategy", "value": "VOLUME_VALUE"}
                                ],
                                value="SMA_CROSSOVER",
                                searchable=False
                            )
                        ], md=12),
                    ], className="mb-3"),
                    
                    # Campos específicos de SMA Crossover
                    html.Div(id="sma-crossover-fields", children=[
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Fast Period"),
                                dbc.Input(id="config-fast-period", type="number", value=15, min=1)
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Slow Period"),
                                dbc.Input(id="config-slow-period", type="number", value=40, min=1)
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Trend Filter Period (opcional)"),
                                dbc.Input(id="config-trend-period", type="number", value="", placeholder="Ej: 100", min=1)
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Usar EMA"),
                                dbc.Checklist(
                                    id="config-use-ema",
                                    options=[{"label": "Usar EMA en lugar de SMA", "value": "yes"}],
                                    value=[]
                                )
                            ], md=3),
                        ]),
                    ]),
                    
                    # Campos específicos de Funnel Logic
                    html.Div(id="funnel-logic-fields", style={"display": "none"}, children=[
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("EMA Period (Contexto)"),
                                dbc.Input(id="config-ema-period", type="number", value=200, min=1)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Delta Confirmation Candles"),
                                dbc.Input(id="config-delta-confirmation-candles", type="number", value=2, min=1)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Delta Lookback"),
                                dbc.Input(id="config-delta-lookback", type="number", value=3, min=1)
                            ], md=4),
                        ]),
                    ]),
                    
                    # Campos específicos de Volume Value Strategy
                    html.Div(id="volume-value-fields", style={"display": "none"}, children=[
                        html.H6("Parámetros de Volume Value Strategy (AMT)", className="mt-3 mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("VWAP Period (días)"),
                                dbc.Input(id="config-vwap-period-days", type="number", value=7, min=1, placeholder="7")
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Volume Profile Period"),
                                dbc.Input(id="config-volume-profile-period", type="number", value=7, min=1, placeholder="7")
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Value Area %"),
                                dbc.Input(id="config-value-area-percent", type="number", value=68, min=1, max=100, step=1, placeholder="68")
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Delta Lookback (CVD)"),
                                dbc.Input(id="config-delta-lookback-vv", type="number", value=20, min=1, placeholder="20")
                            ], md=3),
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Volatility Threshold (%)"),
                                dbc.Input(id="config-volatility-threshold", type="number", value=300, min=100, step=10, placeholder="300")
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Min Volume Period"),
                                dbc.Input(id="config-min-volume-period", type="number", value=20, min=1, placeholder="20")
                            ], md=3),
                            dbc.Col([
                                dbc.Label("LVN Lookback"),
                                dbc.Input(id="config-lvn-lookback", type="number", value=50, min=1, placeholder="50")
                            ], md=3),
                            dbc.Col([], md=3),
                        ]),
                        html.P([
                            html.Small([
                                "ℹ️ ",
                                html.Strong("Nota:"), " VWAP Period en días (7 = semanal para 4H). ",
                                "Value Area % estándar AMT es 68%. ",
                                "Volatility Threshold en % (300% = 3.0x promedio de volumen)."
                            ], className="text-muted")
                        ], className="mt-2"),
                    ]),
                    
                    # Campos compartidos (RSI) - Solo para SMA y Funnel
                    html.Div(id="rsi-fields", children=[
                        html.Hr(),
                        html.H5("Parámetros RSI"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("RSI Period"),
                                dbc.Input(id="config-rsi-period", type="number", value=14, min=2)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("RSI Overbought"),
                                dbc.Input(id="config-rsi-overbought", type="number", value=70.0, step=1.0)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("RSI Oversold"),
                                dbc.Input(id="config-rsi-oversold", type="number", value=30.0, step=1.0)
                            ], md=4),
                        ], className="mt-3"),
                    ]),
                    
                    # Filtro de Volumen - Solo para SMA y Funnel
                    html.Div(id="volume-filter-fields", children=[
                        html.Hr(),
                        html.H5("Filtro de Volumen"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Volume Period (opcional)"),
                                dbc.Input(id="config-volume-period", type="number", value="", placeholder="Ej: 20", min=1)
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Volume Ratio Threshold (opcional)"),
                                dbc.Input(id="config-volume-ratio-threshold", type="number", value=1.0, placeholder="Ej: 1.0", step=0.1, min=0)
                            ], md=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Volume Reversal Period (opcional)"),
                                dbc.Input(id="config-volume-reversal-period", type="number", value="", placeholder="Ej: 20", min=1)
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Volume Reversal Threshold (opcional)"),
                                dbc.Input(id="config-volume-reversal-threshold", type="number", value="", placeholder="Ej: 1.5", step=0.1, min=0)
                            ], md=6),
                        ]),
                    ]),
                    
                    # Filtros Críticos (ATR y Regímenes) - Solo para SMA y Funnel
                    html.Div(id="critical-filters-fields", children=[
                        html.Hr(),
                        html.H5("Filtros Críticos (ATR y Regímenes de Mercado)"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("ATR Period (opcional, para stops dinámicos)"),
                                dbc.Input(id="config-atr-period", type="number", value=14, placeholder="Ej: 14", min=1)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("ATR Multiplier (opcional)"),
                                dbc.Input(id="config-atr-multiplier", type="number", value=1.8, placeholder="Ej: 1.8", step=0.1, min=0.1)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Usar ATR para Stop Loss"),
                                dbc.Checklist(
                                    id="config-use-atr",
                                    options=[{"label": "Activar", "value": "yes"}],
                                    value=["yes"]  # Activado por defecto
                                )
                            ], md=4),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Market Regime Filter"),
                                dbc.Checklist(
                                    id="config-market-regime-enabled",
                                    options=[{"label": "Activar filtro de regímenes (ADX)", "value": "yes"}],
                                    value=["yes"]  # Activado por defecto para VolumeValueStrategy
                                )
                            ], md=4),
                            dbc.Col([
                                dbc.Label("ADX Period"),
                                dbc.Input(id="config-adx-period", type="number", value=14, min=2)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("ADX Threshold"),
                                dbc.Input(id="config-adx-threshold", type="number", value=30.0, step=0.1, min=0)
                            ], md=4),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Max Volatility Multiplier (opcional)"),
                                dbc.Input(id="config-max-volatility-multiplier", type="number", value="", placeholder="Ej: 3.0", step=0.1, min=0.1)
                            ], md=6),
                            dbc.Col([], md=6),
                        ]),
                    ]),
                    html.Hr(),
                    dbc.Button("Ejecutar Backtest", id="run-backtest-btn", color="primary", size="lg", className="w-100"),
                    html.Div(id="run-backtest-status", className="mt-3")
                ])
            ], md=8, className="mx-auto")
        ])
    ], fluid=True)


@app.callback(
    Output("backtests-content", "children"),
    [Input("main-tabs", "value"), Input("interval-component", "n_intervals")]
)
def render_backtests_tab(tab, n_intervals):
    """Renderizar contenido de la pestaña de backtests."""
    if tab != "backtests-tab":
        return html.Div()
    
    try:
        response = requests.get(f"{API_URL}/api/backtests/")
        response.raise_for_status()
        backtests = response.json()
    except Exception as e:
        logger.error(f"Error obteniendo backtests: {e}")
        return dbc.Alert(f"Error cargando backtests: {str(e)}", color="danger")
    
    if not backtests:
        return dbc.Alert("No hay backtests ejecutados aún.", color="info")
    
    table_rows = []
    for bt in backtests:
        status_badge = dbc.Badge(
            bt["status"],
            color="success" if bt["status"] == "COMPLETED" else "warning" if bt["status"] == "RUNNING" else "danger",
            className="me-2"
        )
        
        table_rows.append(html.Tr([
            html.Td(bt["id"]),
            html.Td(bt.get("name", "N/A")),
            html.Td(status_badge),
            html.Td(bt["symbol"]),
            html.Td(bt["timeframe"]),
            html.Td(f"{bt.get('total_return_pct', 0):.2f}%" if bt.get('total_return_pct') else "N/A"),
            html.Td(datetime.fromisoformat(bt["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")),
            html.Td(
                dbc.Button("Ver", id={"type": "view-backtest", "index": bt["id"]}, size="sm", color="primary")
            )
        ]))
    
    table = dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("ID"),
                html.Th("Nombre"),
                html.Th("Estado"),
                html.Th("Símbolo"),
                html.Th("Timeframe"),
                html.Th("Retorno"),
                html.Th("Fecha"),
                html.Th("Acción")
            ])
        ]),
        html.Tbody(table_rows)
    ], bordered=True, hover=True, responsive=True)
    
    return dbc.Container([
        html.H3("Backtests Ejecutados"),
        html.Div(id="backtest-detail"),
        table
    ], fluid=True)


# Callback para actualizar valores por defecto según estrategia y símbolo
@app.callback(
    [
        Output("config-leverage", "value"),
        Output("config-trailing-activation", "value"),
        Output("config-trailing-distance", "value"),
        Output("config-stop-loss", "value"),
        Output("config-atr-multiplier", "value"),
        Output("config-adx-threshold", "value"),
        Output("config-market-regime-enabled", "value")
    ],
    [Input("config-strategy-type", "value"), Input("config-symbol", "value")]
)
def update_default_values_for_strategy(strategy_type, symbol):
    """Actualiza valores por defecto según estrategia y símbolo (configuración conservadora optimizada)."""
    if strategy_type == "VOLUME_VALUE":
        # Configuración conservadora optimizada según símbolo
        if symbol == "BTC/USDT":
            return (
                8.0,      # Leverage
                1.5,      # Trailing Stop Activation (%)
                1.0,      # Trailing Stop Distance (%)
                2.5,      # Hard Stop Loss (%)
                1.8,      # ATR Multiplier
                30.0,     # ADX Threshold
                ["yes"]   # Market Regime Enabled (checked)
            )
        else:  # Altcoins (ETH, SOL, XRP)
            return (
                5.0,      # Leverage
                2.0,      # Trailing Stop Activation (%)
                1.5,      # Trailing Stop Distance (%)
                4.0,      # Hard Stop Loss (%)
                1.8,      # ATR Multiplier
                30.0,     # ADX Threshold
                ["yes"]   # Market Regime Enabled (checked)
            )
    else:
        # Para otras estrategias, mantener valores por defecto originales
        return (
            10.0,     # Leverage
            5.0,      # Trailing Stop Activation
            2.0,      # Trailing Stop Distance
            None,     # Stop Loss (vacío)
            1.8,      # ATR Multiplier (mantener)
            25.0,     # ADX Threshold (default para otras estrategias)
            []        # Market Regime (desactivado por defecto para otras)
        )

# Callback para mostrar/ocultar campos según estrategia
@app.callback(
    [
        Output("sma-crossover-fields", "style"), 
        Output("funnel-logic-fields", "style"),
        Output("volume-value-fields", "style"),
        Output("rsi-fields", "style"),
        Output("volume-filter-fields", "style"),
        Output("critical-filters-fields", "style")
    ],
    Input("config-strategy-type", "value")
)
def update_strategy_fields(strategy_type):
    """Mostrar/ocultar campos según la estrategia seleccionada."""
    if strategy_type == "SMA_CROSSOVER":
        # SMA: Mostrar todos los campos
        return (
            {"display": "block"},  # sma-crossover-fields
            {"display": "none"},   # funnel-logic-fields
            {"display": "none"},   # volume-value-fields
            {"display": "block"},  # rsi-fields
            {"display": "block"},  # volume-filter-fields
            {"display": "block"}   # critical-filters-fields
        )
    elif strategy_type == "FUNNEL_LOGIC":
        # Funnel: Mostrar RSI y filtros, ocultar SMA
        return (
            {"display": "none"},   # sma-crossover-fields
            {"display": "block"},  # funnel-logic-fields
            {"display": "none"},   # volume-value-fields
            {"display": "block"},  # rsi-fields
            {"display": "block"},  # volume-filter-fields
            {"display": "block"}   # critical-filters-fields
        )
    elif strategy_type == "VOLUME_VALUE":
        # Volume Value: Mostrar sus propios campos + filtros ATR y ADX
        return (
            {"display": "none"},   # sma-crossover-fields
            {"display": "none"},   # funnel-logic-fields
            {"display": "block"},  # volume-value-fields
            {"display": "none"},   # rsi-fields (VolumeValueStrategy no usa RSI)
            {"display": "none"},   # volume-filter-fields (usa su propio sistema)
            {"display": "block"}   # critical-filters-fields (ATR y ADX para gestión de riesgo)
        )
    else:
        # Default: Mostrar SMA
        return (
            {"display": "block"},
            {"display": "none"},
            {"display": "none"},
            {"display": "block"},
            {"display": "block"},
            {"display": "block"}
        )


@app.callback(
    Output("run-backtest-status", "children"),
    Input("run-backtest-btn", "n_clicks"),
    State("config-name", "value"),
    State("config-symbol", "value"),
    State("config-market-type", "value"),
    State("config-timeframe", "value"),
    State("config-days", "value"),
    State("config-initial-capital", "value"),
    State("config-commission", "value"),
    State("config-leverage", "value"),
    State("config-stop-loss", "value"),
    State("config-take-profit", "value"),
    State("config-trailing-activation", "value"),
    State("config-trailing-distance", "value"),
    State("config-strategy-type", "value"),
    State("config-fast-period", "value"),
    State("config-slow-period", "value"),
    State("config-use-ema", "value"),
    State("config-trend-period", "value"),
    State("config-rsi-period", "value"),
    State("config-rsi-overbought", "value"),
    State("config-rsi-oversold", "value"),
    State("config-ema-period", "value"),
    State("config-delta-confirmation-candles", "value"),
    State("config-delta-lookback", "value"),
    State("config-vwap-period-days", "value"),
    State("config-volume-profile-period", "value"),
    State("config-value-area-percent", "value"),
    State("config-delta-lookback-vv", "value"),
    State("config-volatility-threshold", "value"),
    State("config-min-volume-period", "value"),
    State("config-lvn-lookback", "value"),
    State("config-volume-period", "value"),
    State("config-volume-ratio-threshold", "value"),
    State("config-volume-reversal-period", "value"),
    State("config-volume-reversal-threshold", "value"),
    State("config-atr-period", "value"),
    State("config-atr-multiplier", "value"),
    State("config-use-atr", "value"),
    State("config-market-regime-enabled", "value"),
    State("config-adx-period", "value"),
    State("config-adx-threshold", "value"),
    State("config-max-volatility-multiplier", "value"),
    prevent_initial_call=True
)
def run_backtest_callback(n_clicks, name, symbol, market_type, timeframe, days, initial_capital,
                          commission, leverage, stop_loss, take_profit, trailing_activation,
                          trailing_distance, strategy_type, fast_period, slow_period, use_ema,
                          trend_period, rsi_period, rsi_overbought, rsi_oversold,
                          ema_period, delta_confirmation_candles, delta_lookback,
                          vwap_period_days, volume_profile_period, value_area_percent,
                          delta_lookback_vv, volatility_threshold, min_volume_period, lvn_lookback,
                          volume_period, volume_ratio_threshold,
                          volume_reversal_period, volume_reversal_threshold,
                          atr_period, atr_multiplier, use_atr, market_regime_enabled,
                          adx_period, adx_threshold, max_volatility_multiplier):
    """Callback para ejecutar backtest."""
    if not n_clicks:
        return html.Div()
    
    try:
        # Para VolumeValueStrategy: usar hard stop como respaldo incluso si ATR está activo
        # El Backtester elegirá el más conservador entre ATR y hard stop
        if strategy_type == "VOLUME_VALUE" and stop_loss:
            stop_loss_pct_value = float(stop_loss) / 100.0
        elif use_atr and len(use_atr) > 0 and atr_period and atr_multiplier:
            stop_loss_pct_value = None  # Solo ATR
        else:
            stop_loss_pct_value = (float(stop_loss) / 100.0 if stop_loss else None)
        
        config = {
            "name": name,
            "symbol": symbol,
            "market_type": market_type,
            "timeframe": timeframe,
            "days": days,
            "initial_capital": float(initial_capital),
            "commission": float(commission) / 100.0,  # Convertir porcentaje a decimal
            "leverage": float(leverage) if leverage else 10.0,
            "stop_loss_pct": stop_loss_pct_value,
            "take_profit_pct": float(take_profit) / 100.0 if take_profit else 0.08,
            "trailing_stop_activation": float(trailing_activation) / 100.0,
            "trailing_stop_distance": float(trailing_distance) / 100.0,
            "strategy_type": strategy_type or "SMA_CROSSOVER",
            # Parámetros SMA Crossover
            "fast_period": int(fast_period) if fast_period else 15,
            "slow_period": int(slow_period) if slow_period else 40,
            "use_ema": use_ema and len(use_ema) > 0 if use_ema else False,
            "trend_filter_period": int(trend_period) if trend_period else None,
            # Parámetros compartidos
            "rsi_period": int(rsi_period) if rsi_period else None,
            "rsi_overbought": float(rsi_overbought) if rsi_overbought else None,
            "rsi_oversold": float(rsi_oversold) if rsi_oversold else None,
            # Parámetros Funnel Logic
            "ema_period": int(ema_period) if ema_period else None,
            "delta_confirmation_candles": int(delta_confirmation_candles) if delta_confirmation_candles else None,
            "delta_lookback": int(delta_lookback) if delta_lookback else None,
            "volume_period": int(volume_period) if volume_period else None,
            "volume_ratio_threshold": float(volume_ratio_threshold) if volume_ratio_threshold else None,
            "volume_reversal_period": int(volume_reversal_period) if volume_reversal_period else None,
            "volume_reversal_threshold": float(volume_reversal_threshold) if volume_reversal_threshold else None,
            "atr_period": int(atr_period) if (atr_period and use_atr and len(use_atr) > 0) else None,
            "atr_multiplier": float(atr_multiplier) if (atr_multiplier and use_atr and len(use_atr) > 0) else None,
            "market_regime_enabled": len(market_regime_enabled) > 0 if market_regime_enabled else False,
            "adx_period": int(adx_period) if adx_period else 14,
            "adx_threshold": float(adx_threshold) if adx_threshold else (30.0 if strategy_type == "VOLUME_VALUE" else 25.0),
            "max_volatility_multiplier": float(max_volatility_multiplier) if max_volatility_multiplier else None,
            # Parámetros Volume Value Strategy
            "vwap_period_days": int(vwap_period_days) if vwap_period_days else None,
            "volume_profile_period": int(volume_profile_period) if volume_profile_period else None,
            "value_area_percent": float(value_area_percent) / 100.0 if value_area_percent else None,
            "delta_lookback_vv": int(delta_lookback_vv) if delta_lookback_vv else None,
            "volatility_threshold": float(volatility_threshold) / 100.0 if volatility_threshold else None,
            "min_volume_period": int(min_volume_period) if min_volume_period else None,
            "lvn_lookback": int(lvn_lookback) if lvn_lookback else None
        }
        
        response = requests.post(f"{API_URL}/api/backtests/run", json=config)
        response.raise_for_status()
        result = response.json()
        
        return dbc.Alert(
            f"Backtest iniciado exitosamente! ID: {result['id']}. Revisa la pestaña 'Backtests' para ver el progreso.",
            color="success"
        )
    except Exception as e:
        logger.error(f"Error ejecutando backtest: {e}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# ==================== Callbacks para Resultados, Operaciones y Señales ====================

@app.callback(
    Output("results-content", "children"),
    [Input("main-tabs", "value"), Input("selected-backtest-store", "data")]
)
def render_results_tab(tab, selected_backtest_id):
    """Renderizar contenido de la pestaña de resultados."""
    if tab != "results-tab" or not selected_backtest_id:
        return dbc.Alert("Por favor selecciona un backtest desde la pestaña 'Backtests'", color="info")
    
    try:
        response = requests.get(f"{API_URL}/api/backtests/{selected_backtest_id}")
        response.raise_for_status()
        backtest = response.json()
    except Exception as e:
        return dbc.Alert(f"Error cargando backtest: {str(e)}", color="danger")
    
    if backtest["status"] != "COMPLETED":
        return dbc.Alert(f"Backtest en estado: {backtest['status']}. Espera a que complete.", color="warning")
    
    metrics_cards = dbc.Row([
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Capital Inicial"), html.H2(f"${backtest.get('initial_capital', 0):,.2f}", className="text-secondary")])])], md=2),
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Capital Final"), html.H2(f"${backtest.get('final_capital', backtest.get('initial_capital', 0)):,.2f}", className="text-success")])])], md=2),
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Retorno Total"), html.H2(f"{backtest.get('total_return_pct', 0):.2f}%", className="text-success")])])], md=2),
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Sharpe Ratio"), html.H2(f"{backtest.get('sharpe_ratio', 0):.2f}", className="text-info")])])], md=2),
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Win Rate"), html.H2(f"{backtest.get('win_rate', 0)*100:.1f}%", className="text-primary")])])], md=2),
        dbc.Col([dbc.Card([dbc.CardBody([html.H4("Profit Factor"), html.H2(f"{backtest.get('profit_factor', 0):.2f}", className="text-warning")])])], md=2),
    ], className="mb-4")
    
    # Obtener datos de señales para visualizar VWAP y VPOC (si es VolumeValueStrategy)
    strategy_config = backtest.get('strategy_config', {})
    strategy_type = strategy_config.get('strategy_type', '') if isinstance(strategy_config, dict) else ''
    
    # Crear gráfico de Equity Curve
    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(x=[0, 1], y=[backtest.get('initial_capital', 5000), backtest.get('final_capital', 5000)], mode='lines', name='Capital', line=dict(color='green', width=2)))
    equity_fig.update_layout(title="Equity Curve", xaxis_title="Tiempo", yaxis_title="Capital ($)", height=400)
    
    # Si es VolumeValueStrategy, agregar visualización de VWAP y VPOC
    vwap_vpoc_fig = None
    if strategy_type == 'VOLUME_VALUE':
        try:
            # Obtener señales con información de VWAP y VPOC
            signals_response = requests.get(f"{API_URL}/api/signals/?backtest_id={selected_backtest_id}&limit=10000")
            signals_response.raise_for_status()
            signals = signals_response.json()
            
            if signals:
                signals_df = pd.DataFrame(signals)
                
                # Filtrar señales con valores de VWAP y VPOC
                signals_with_vwap = signals_df[signals_df['vwap_value'].notna()]
                signals_with_vpoc = signals_df[signals_df['vpoc_level'].notna()]
                
                # Crear gráfico de precios con VWAP y VPOC
                vwap_vpoc_fig = go.Figure()
                
                # Agregar VWAP si hay datos
                if len(signals_with_vwap) > 0:
                    vwap_vpoc_fig.add_trace(go.Scatter(
                        x=pd.to_datetime(signals_with_vwap['timestamp']),
                        y=signals_with_vwap['vwap_value'],
                        mode='lines',
                        name='VWAP',
                        line=dict(color='blue', width=2, dash='dash')
                    ))
                
                # Agregar VPOC como línea horizontal si hay datos
                if len(signals_with_vpoc) > 0:
                    vpoc_value = signals_with_vpoc['vpoc_level'].iloc[0]  # Usar primer VPOC
                    vwap_vpoc_fig.add_hline(
                        y=vpoc_value,
                        line_dash="dot",
                        line_color="orange",
                        annotation_text=f"VPOC: ${vpoc_value:.2f}",
                        annotation_position="right"
                    )
                
                # Agregar precios de señales
                if len(signals) > 0:
                    buy_signals = signals_df[signals_df['signal_type'] == 'BUY']
                    sell_signals = signals_df[signals_df['signal_type'] == 'SELL']
                    
                    if len(buy_signals) > 0:
                        vwap_vpoc_fig.add_trace(go.Scatter(
                            x=pd.to_datetime(buy_signals['timestamp']),
                            y=buy_signals['price'],
                            mode='markers',
                            name='Señales Compra',
                            marker=dict(color='green', size=10, symbol='triangle-up')
                        ))
                    
                    if len(sell_signals) > 0:
                        vwap_vpoc_fig.add_trace(go.Scatter(
                            x=pd.to_datetime(sell_signals['timestamp']),
                            y=sell_signals['price'],
                            mode='markers',
                            name='Señales Venta',
                            marker=dict(color='red', size=10, symbol='triangle-down')
                        ))
                
                vwap_vpoc_fig.update_layout(
                    title="Precio con VWAP y VPOC (Volume Value Strategy)",
                    xaxis_title="Tiempo",
                    yaxis_title="Precio ($)",
                    height=400
                )
        except Exception as e:
            logger.warning(f"Error obteniendo datos para VWAP/VPOC: {e}")
            vwap_vpoc_fig = None
    
    # Construir contenido
    content = [html.H3(f"Resultados - {backtest.get('name', 'Backtest')}"), metrics_cards]
    
    # Agregar gráficos
    if vwap_vpoc_fig:
        graphs_row = dbc.Row([
            dbc.Col([dcc.Graph(figure=equity_fig)], md=6),
            dbc.Col([dcc.Graph(figure=vwap_vpoc_fig)], md=6)
        ])
    else:
        graphs_row = dbc.Row([dbc.Col([dcc.Graph(figure=equity_fig)])])
    
    content.append(graphs_row)
    
    return dbc.Container(content, fluid=True)


@app.callback(
    Output("trades-content", "children"),
    [Input("main-tabs", "value"), Input("selected-backtest-store", "data")]
)
def render_trades_tab(tab, selected_backtest_id):
    """Renderizar contenido de la pestaña de operaciones."""
    if tab != "trades-tab" or not selected_backtest_id:
        return dbc.Alert("Por favor selecciona un backtest desde la pestaña 'Backtests'", color="info")
    
    try:
        response = requests.get(f"{API_URL}/api/trades/?backtest_id={selected_backtest_id}")
        response.raise_for_status()
        trades = response.json()
    except Exception as e:
        return dbc.Alert(f"Error cargando operaciones: {str(e)}", color="danger")
    
    if not trades:
        return dbc.Alert("No hay operaciones para este backtest.", color="info")
    
    df = pd.DataFrame(trades)
    
    # Redondear P&L a 2 decimales
    if 'pnl_dollar' in df.columns:
        df['pnl_dollar'] = df['pnl_dollar'].round(2)
    if 'pnl_percent' in df.columns:
        df['pnl_percent'] = df['pnl_percent'].round(2)
    
    pnl_fig = px.bar(df, x=df.index, y="pnl_dollar", color="pnl_dollar", color_continuous_scale=["red", "green"], title="P&L por Operación")
    pnl_fig.update_layout(height=400, xaxis_title="Operación #", yaxis_title="P&L ($)")
    
    # Seleccionar columnas para mostrar (incluir stop_loss_price si existe)
    columns_to_show = ["fecha_entrada", "fecha_salida", "tipo", "precio_entrada", "precio_salida"]
    if 'stop_loss_price' in df.columns:
        columns_to_show.append("stop_loss_price")
    columns_to_show.extend(["pnl_dollar", "pnl_percent"])
    
    # Filtrar columnas que existen
    columns_to_show = [col for col in columns_to_show if col in df.columns]
    
    table = dbc.Table.from_dataframe(df[columns_to_show].head(50), bordered=True, hover=True, responsive=True, striped=True)
    
    return dbc.Container([html.H3("Operaciones"), dcc.Graph(figure=pnl_fig), html.H4("Detalle de Operaciones"), table], fluid=True)


@app.callback(
    Output("signals-content", "children"),
    [Input("main-tabs", "value"), Input("selected-backtest-store", "data")]
)
def render_signals_tab(tab, selected_backtest_id):
    """Renderizar contenido de la pestaña de señales."""
    if tab != "signals-tab" or not selected_backtest_id:
        return dbc.Alert("Por favor selecciona un backtest desde la pestaña 'Backtests'", color="info")
    
    try:
        response = requests.get(f"{API_URL}/api/signals/?backtest_id={selected_backtest_id}&limit=1000")
        response.raise_for_status()
        signals = response.json()
    except Exception as e:
        return dbc.Alert(f"Error cargando señales: {str(e)}", color="danger")
    
    if not signals:
        return dbc.Alert("No hay señales para este backtest.", color="info")
    
    df = pd.DataFrame(signals)
    signal_fig = go.Figure()
    signal_fig.add_trace(go.Scatter(x=df["timestamp"], y=df["price"], mode='lines', name='Precio', line=dict(color='blue', width=1)))
    
    buy_signals = df[df["signal_type"] == "BUY"]
    if not buy_signals.empty:
        signal_fig.add_trace(go.Scatter(x=buy_signals["timestamp"], y=buy_signals["price"], mode='markers', name='Compra', marker=dict(color='green', size=10, symbol='triangle-up')))
    
    sell_signals = df[df["signal_type"] == "SELL"]
    if not sell_signals.empty:
        signal_fig.add_trace(go.Scatter(x=sell_signals["timestamp"], y=sell_signals["price"], mode='markers', name='Venta', marker=dict(color='red', size=10, symbol='triangle-down')))
    
    signal_fig.update_layout(title="Señales de Trading", xaxis_title="Fecha", yaxis_title="Precio", height=600)
    
    return dbc.Container([html.H3("Señales Generadas"), dcc.Graph(figure=signal_fig)], fluid=True)


@app.callback(
    Output("selected-backtest-store", "data"),
    Input({"type": "view-backtest", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def select_backtest(n_clicks):
    """Callback para seleccionar un backtest."""
    if not any(n_clicks):
        return dash.no_update
    
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    import json
    button_id_dict = json.loads(button_id)
    return button_id_dict["index"]


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
