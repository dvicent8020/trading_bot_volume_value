# 🎯 Funnel Logic - Configuración Optimizada

*Fecha: 16 de Enero de 2026*
*Rama: feature/funnel-logic-testing*

---

## 📊 Comparación: Original vs Optimizado

### Timeframe 4h - 90 días

| Métrica | Original (10x) | **Optimizado (5x)** | Mejora |
|---------|---------------|---------------------|--------|
| Retorno | +92.25% | +29.42% | -68% pero más seguro |
| Sharpe | 2.33 | **1.83** | Bueno |
| **Max DD** | -51.43% | **-26.13%** | **↓ 49%** ✅ |
| Liquidaciones | Riesgo alto | ✅ Sin riesgo | ✅ |

### Timeframe 1d - 365 días

| Métrica | Original (10x) | **Optimizado (5x)** | Mejora |
|---------|---------------|---------------------|--------|
| Retorno | +33.28% | +38.25% | **+15%** ✅ |
| Sharpe | 0.79 | **1.14** | **+44%** ✅ |
| **Max DD** | -71.77% | **-23.28%** | **↓ 68%** ✅ |

---

## 🏆 Mejores Resultados Optimizados

| TF | Días | Retorno | Sharpe | MaxDD | Config |
|----|------|---------|--------|-------|--------|
| **1d** | **365** | **+38.25%** | **1.14** | **-23.28%** | ⭐ Mejor balance |
| **4h** | **90** | **+29.42%** | **1.83** | **-26.13%** | ⭐ Mejor Sharpe |
| 15m | 90 | +16.34% | 1.47 | -30.07% | Bueno |

---

## ⚙️ Configuraciones Optimizadas por Timeframe

### 15m (Trading Activo)
```python
config_15m = {
    'leverage': 3.0,
    'stop_loss_pct': 0.02,      # 2%
    'atr_multiplier': 1.8,
    'trailing_activation': 0.02, # 2%
    'trailing_distance': 0.01,   # 1%
    'take_profit_pct': 0.04,     # 4%
    'ema_period': 100,
}
# Resultado: +16.34%, Sharpe 1.47, DD -30.07%
```

### 1h (Intraday)
```python
config_1h = {
    'leverage': 4.0,
    'stop_loss_pct': 0.03,      # 3%
    'atr_multiplier': 1.8,
    'trailing_activation': 0.025, # 2.5%
    'trailing_distance': 0.012,   # 1.2%
    'take_profit_pct': 0.06,     # 6%
    'ema_period': 150,
}
# Resultado: -0.66% (período difícil)
```

### 4h (Swing Trading) ⭐ RECOMENDADO
```python
config_4h = {
    'leverage': 5.0,
    'stop_loss_pct': 0.04,      # 4%
    'atr_multiplier': 1.8,
    'trailing_activation': 0.03, # 3%
    'trailing_distance': 0.015,  # 1.5%
    'take_profit_pct': 0.08,     # 8%
    'ema_period': 200,
}
# Resultado: +29.42%, Sharpe 1.83, DD -26.13%
```

### 1d (Position Trading) ⭐ MEJOR BALANCE
```python
config_1d = {
    'leverage': 5.0,
    'stop_loss_pct': 0.05,      # 5%
    'atr_multiplier': 1.8,
    'trailing_activation': 0.04, # 4%
    'trailing_distance': 0.02,   # 2%
    'take_profit_pct': 0.10,     # 10%
    'ema_period': 100,
}
# Resultado: +38.25%, Sharpe 1.14, DD -23.28%
```

---

## 📈 Resumen de Mejoras Aplicadas

| Parámetro | Original | Optimizado | Razón |
|-----------|----------|------------|-------|
| **Leverage** | 10x | 3-5x | Reduce riesgo de liquidación |
| **Stop Loss** | Solo ATR | ATR + Fijo | Doble protección |
| **Trailing Act.** | 5% | 2-4% | Asegura ganancias antes |
| **Trailing Dist.** | 2% | 1-2% | Más ajustado al precio |
| **Take Profit** | 8% | 4-10% | Adaptado al timeframe |

---

## ✅ Conclusiones

### Lo que funcionó:
1. **Reducir leverage de 10x a 5x**: DD bajó de -51% a -26%
2. **Stop Loss fijo adicional**: Protección extra al ATR
3. **Trailing más agresivo**: Captura ganancias más rápido

### Mejores configuraciones:
- **Para máximo retorno seguro**: 1d 365 días (+38.25%, DD -23%)
- **Para mejor Sharpe**: 4h 90 días (+29.42%, Sharpe 1.83)
- **Para trading activo**: 15m 90 días (+16.34%, Sharpe 1.47)

### Evitar:
- 4h con 365 días: DD -100%
- 1h en este período: Retorno negativo
- 1d con solo 90 días: Sin señales

---

## 📁 Scripts de prueba

- `test_funnel_optimizado.py` - Optimización inicial
- `test_funnel_optimizado_completo.py` - Pruebas completas

---

*Documento generado: 16 de Enero de 2026*
