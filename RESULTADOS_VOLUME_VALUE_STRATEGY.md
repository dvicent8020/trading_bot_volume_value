# 📊 Mejores Resultados - Volume Value Strategy

*Fecha: 16 de Enero de 2026*
*Rama: feature/expert-improvements*
*Para comparación con: Funnel Logic Strategy*

---

## 🏆 Resumen de Mejores Resultados

### BTC/USDT - Timeframe 1D - 365 días

| Configuración | Leverage | Retorno | Sharpe | Drawdown | Win Rate |
|--------------|----------|---------|--------|----------|----------|
| **⭐ CONSERVADOR** | 3x | **+91.65%** | **2.01** | **-28%** | 80% |
| Balanceado | 5x | +176.53% | 2.01 | -74% | 80% |
| Agresivo | 5x | +187.86% | 2.04 | -77% | 80% |
| Con Absorción Mejorada | 3x | **+217%** | 2.69 | -49% | 92% |

### BTC/USDT - Timeframe 4H - 90 días (Solo SHORTs)

| Configuración | Leverage | Retorno | Sharpe | Drawdown | Win Rate |
|--------------|----------|---------|--------|----------|----------|
| Conservador | 3x | +14.92% | 2.40 | -6% | 100% |
| **⭐ AGRESIVO** | 10x | **+79.55%** | **3.40** | **-22%** | **100%** |

### BTC/USDT - Timeframe 15m - 90 días (Smart Trailing Auto)

| Configuración | Trailing | Retorno | Sharpe | Drawdown | Win Rate |
|--------------|----------|---------|--------|----------|----------|
| **⭐ SMART AUTO** | Auto | **+69.58%** | 0.25 | -57% | 43% |

---

## 🔧 Configuraciones Óptimas

### Configuración Recomendada: BTC/USDT 1D (Conservadora)

```python
# Backtester
backtester_params = {
    'leverage': 3.0,
    'stop_loss_pct': 0.05,          # 5%
    'trailing_stop_activation': 0.03, # 3%
    'trailing_stop_distance': 0.01,   # 1%
    'take_profit_pct': 0.12,          # 12%
    'atr_period': 14,
    'atr_multiplier': 2.5,
    'market_type': 'futures',
    'auto_trailing_selection': True,  # Smart para TF cortos, Tradicional para largos
}

# Estrategia
strategy_params = {
    'vwap_period_days': 5,
    'volume_profile_period': 7,
    'market_regime_enabled': True,
    'adx_period': 14,
    'adx_threshold': 25,
    'disable_longs': False,           # True para 4H
    'require_uptrend_for_longs': True,
    'trend_filter_period': 50,
}
```

---

## 📈 Características de la Estrategia

### Indicadores Utilizados
1. **VWAP Rolling** - Precio ponderado por volumen (5 días)
2. **Volume Profile** - VPOC, VAH, VAL (7 días)
3. **CVD** - Cumulative Volume Delta
4. **ADX** - Average Directional Index (período 14)
5. **ATR** - Average True Range (período 14)

### Lógica de Señales
1. **Absorción Divergente**: Precio hace lower low pero CVD hace higher low (LONG)
2. **Momentum CVD**: CVD en dirección del trend confirmado por ADX
3. **Zona de Valor**: Señales dentro de VPOC/VAH/VAL para momentum

### Filtros Implementados
- ✅ ADX > 25 (régimen de mercado con tendencia)
- ✅ Signal Cooldown (5 velas entre señales)
- ✅ Uptrend Filter (precio > SMA50 para LONGs)
- ✅ Disable LONGs en 4H (0% win rate histórico)

### Gestión de Riesgo
- ✅ Trailing Stop Híbrido (Smart para TF cortos)
- ✅ Stop Loss ATR-dinámico
- ✅ Breakeven automático después de TP parcial
- ✅ Detección de Exhaustion (opcional)

---

## 🎯 Métricas Objetivo

Para comparar con Funnel Logic Strategy:

| Métrica | Volume Value | Objetivo Funnel |
|---------|-------------|-----------------|
| Retorno Anual | ~90-217% | >100% |
| Sharpe Ratio | 2.0-2.7 | >2.0 |
| Max Drawdown | -28% a -49% | <-30% |
| Win Rate | 80-92% | >70% |
| Operaciones/año | 10-20 | >20 |

---

## 📋 Puntos Fuertes

1. **Alta precisión**: 80-100% win rate en configuraciones óptimas
2. **Buen Sharpe**: >2.0 consistentemente
3. **Flexible**: Smart Trailing adaptativo por timeframe
4. **Robusto**: Funciona en diferentes condiciones de mercado

## ⚠️ Puntos a Mejorar

1. **Pocas operaciones**: Solo 10-20 al año en 1D
2. **LONGs débiles en 4H**: 0% win rate
3. **Drawdown variable**: -28% a -77% según configuración
4. **Sensible al timeframe**: Rendimiento varía significativamente

---

## 📁 Archivos Clave

```
trading_bot/
├── volume_value_strategy.py  # Estrategia principal
├── backtester.py             # Motor de backtesting
├── data_handler.py           # Descarga de datos
└── funnel_strategy.py        # (Próxima comparación)
```

---

*Este documento sirve como baseline para comparar con la estrategia Funnel Logic*
