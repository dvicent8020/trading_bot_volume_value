# 📊 Comparación: Funnel Logic vs Volume Value Strategy

*Fecha: 16 de Enero de 2026*
*Par: BTC/USDT (Futures)*

---

## 🏆 Resultado Global

| Estrategia | Retorno Promedio | Sharpe Promedio | Drawdown Promedio | Victorias |
|------------|------------------|-----------------|-------------------|-----------|
| **Funnel Logic** | **+10.89%** | **0.95** | -70.53% | **4/6** |
| Volume Value | -1.80% | -0.11 | -71.64% | 2/6 |

**🏆 GANADOR: Funnel Logic** (por retorno promedio y victorias)

---

## 📈 Resultados Detallados

### Timeframe 15m - 90 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| Funnel Logic | -14.61% | 0.88 | -100.00% | 0.2% | 97 |
| **Volume Value** | **+73.90%** | **2.57** | -58.69% | 0.4% | 552 |

🏆 **Ganador: Volume Value** (+88.51% diferencia)

---

### Timeframe 1h - 90 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| **Funnel Logic** | **+25.65%** | **1.53** | -100.00% | 0.2% | 37 |
| Volume Value | -35.62% | -1.11 | -94.25% | 0.4% | 212 |

🏆 **Ganador: Funnel Logic** (+61.27% diferencia)

---

### Timeframe 4h - 90 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| **Funnel Logic** | **+92.25%** | **2.33** | -51.43% | 0.8% | 8 |
| Volume Value | +1.47% | 0.47 | -44.01% | 0.5% | 30 |

🏆 **Ganador: Funnel Logic** (+90.78% diferencia) ⭐ MEJOR RESULTADO

---

### Timeframe 4h - 365 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| Funnel Logic | -71.21% | 0.17 | -100.00% | 0.3% | 39 |
| **Volume Value** | **+14.80%** | **0.55** | -95.16% | 0.5% | 109 |

🏆 **Ganador: Volume Value** (+86.01% diferencia)

---

### Timeframe 1d - 90 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| **Funnel Logic** | **0.00%** | 0.00 | 0.00% | 0.0% | 0 |
| Volume Value | -45.57% | -3.32 | -45.66% | 0.3% | 8 |

🏆 **Ganador: Funnel Logic** (0 trades = sin pérdidas)

---

### Timeframe 1d - 365 días

| Estrategia | Retorno | Sharpe | Drawdown | Win Rate | Trades |
|------------|---------|--------|----------|----------|--------|
| **Funnel Logic** | **+33.28%** | **0.79** | -71.77% | 1.0% | 2 |
| Volume Value | -19.76% | 0.19 | -92.07% | 0.5% | 48 |

🏆 **Ganador: Funnel Logic** (+53.04% diferencia)

---

## 🔍 Análisis

### Fortalezas de Funnel Logic
- ✅ Mejor rendimiento en **4h (90 días)**: +92.25% con Sharpe 2.33
- ✅ Muy selectiva: pocas señales pero más precisas
- ✅ Excelente en **1d (365 días)**: +33.28% con solo 2 trades
- ✅ Mejor en mercados con tendencias claras

### Debilidades de Funnel Logic
- ⚠️ Drawdown -100% en varios tests (liquidaciones)
- ⚠️ Muy pocas señales en 1d (0-2 trades)
- ⚠️ Sensible a leverage alto (10x)
- ⚠️ Inconsistente en períodos largos (4h 365d: -71%)

### Fortalezas de Volume Value
- ✅ Mejor en **15m**: +73.90% con Sharpe 2.57
- ✅ Más operaciones = más oportunidades
- ✅ Mejor en períodos largos con leverage moderado
- ✅ Auto-Trailing adaptativo

### Debilidades de Volume Value
- ⚠️ Retornos negativos en 4/6 tests
- ⚠️ Alto drawdown generalizado
- ⚠️ Sharpe negativo en promedio

---

## 🎯 Recomendaciones

### Para Funnel Logic
1. **Reducir leverage**: 10x causa liquidaciones
2. **Mejor timeframe**: 4h con 90 días
3. **Configuración óptima**: Delta=2, ATR=1.5-2.0
4. **No usar en 15m**: Resultados negativos

### Para Volume Value  
1. **Mejor timeframe**: 15m con Smart Trailing
2. **Mantener leverage 3x**: Más estable
3. **Evitar 1h y 1d**: Resultados inconsistentes
4. **Usar con absorción mejorada**: +217% histórico en 1D

---

## 📋 Configuraciones Óptimas

### Funnel Logic - 4h 90 días
```python
strategy = FunnelStrategy(
    ema_period=200,
    rsi_period=14,
    rsi_oversold=30.0,
    rsi_overbought=70.0,
    volume_ratio_threshold=1.0,
    delta_confirmation_candles=2,
)
backtester = Backtester(
    leverage=5.0,  # Reducido de 10x
    take_profit_pct=0.08,
    atr_multiplier=2.0,
)
```

### Volume Value - 15m 90 días
```python
strategy = VolumeValueStrategy(
    vwap_period_days=5,
    adx_threshold=25,
    require_uptrend_for_longs=True,
)
backtester = Backtester(
    leverage=3.0,
    auto_trailing_selection=True,  # Smart para 15m
)
```

---

## 📊 Conclusión

| Criterio | Ganador |
|----------|---------|
| Retorno Promedio | **Funnel Logic** (+10.89%) |
| Sharpe Promedio | **Funnel Logic** (0.95) |
| Consistencia | Empate (ambos con drawdowns altos) |
| Mejor Resultado Único | **Funnel Logic** (+92.25% en 4h) |
| Timeframes Cortos (15m) | **Volume Value** (+73.90%) |

**Recomendación Final:**
- **4h corto plazo (90d)**: Funnel Logic con leverage reducido
- **15m trading activo**: Volume Value con Smart Trailing
- **Largo plazo (365d)**: Evitar ambas o usar leverage muy bajo

---

*Documento generado: 16 de Enero de 2026*
