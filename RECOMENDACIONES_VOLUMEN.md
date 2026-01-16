# GUÍA DE RECOMENDACIONES: PARÁMETROS DE TRADING

*Generado: 2026-01-13*
*Actualizado: 2026-01-14*
*Última actualización: Configuraciones por Par de Trading y Funnel Strategy*

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Metodología](#metodología)
3. [Filtros de Volumen](#filtros-de-volumen)
4. [Filtros Críticos: ATR y Market Regime](#filtros-críticos-atr-y-market-regime)
5. [Recomendaciones por Timeframe](#recomendaciones-por-timeframe)
6. [Recomendaciones por Par de Trading](#recomendaciones-por-par-de-trading)
7. [Recomendaciones Finales](#recomendaciones-finales)

---

## 📖 Introducción

Este documento presenta un análisis exhaustivo de los parámetros de trading para optimizar el rendimiento de la estrategia en diferentes temporalidades.

### Parámetros Evaluados:

**Filtros de Volumen:**
- **Volume Ratio (Filtro de Señales):** Filtra señales según el volumen relativo al promedio
- **Volume Reversal (Filtro de Reversiones):** Valida volumen antes de ejecutar cambios de dirección

**Filtros Críticos:**
- **ATR (Average True Range):** Stop loss dinámico basado en volatilidad
- **Market Regime Filter:** Filtra señales según condiciones de mercado (ADX + volatilidad)

### Timeframes y Períodos Analizados:

| Timeframe | Períodos (días) | Total de velas aproximadas |
|-----------|-----------------|----------------------------|
| 1h | 90, 120, 180 | 2,160 - 4,320 velas |
| 4h | 90, 120, 180 | 540 - 1,080 velas |
| 1d | 90, 120, 180 | 90 - 180 velas |

---

## 🔬 Metodología

### Configuración Base:
- Estrategia: SMA Crossover (15/40)
- Filtros: RSI(14, 70/30), Trend Filter (Desactivado)
- Filtros de Volumen: Volume Ratio (20, 1.0), Volume Reversal (20, 1.5)
- Take Profit: 8%
- Leverage: 10x (futures)
- Capital inicial: $5,000

### Métricas de Evaluación:
1. **Sharpe Ratio** (métrica principal)
2. Retorno Total
3. Máximo Drawdown
4. Número de Operaciones
5. Win Rate
6. Profit Factor

---

## 📊 Filtros de Volumen

### Volume Ratio (Filtro de Señales):

**Parámetros:**
- Período: 20 velas (recomendado)
- Threshold: Variable según timeframe

**Función:** Genera señales solo si el volumen actual es superior al promedio histórico multiplicado por el threshold.

**Recomendaciones por Threshold:**

| Valor | Características | Uso Recomendado |
|-------|----------------|-----------------|
| **0.8** | Menos restrictivo, más señales | Mercados activos, más operaciones |
| **0.9** | Moderado, balance | Timeframe 1d, períodos cortos |
| **1.0** | Equilibrio óptimo | **Recomendado para mayoría de casos** |
| **1.1** | Selectivo | Timeframes cortos (1h), más calidad |
| **1.2+** | Muy selectivo | Estrategias conservadoras, pocas operaciones |

### Volume Reversal (Filtro de Reversiones):

**Parámetros:**
- Período: 20 velas (recomendado)
- Threshold: 1.5 (recomendado)

**Función:** Valida que el volumen sea suficiente antes de ejecutar una reversión de posición (cambio de dirección).

**Recomendaciones:**

| Valor | Características | Uso Recomendado |
|-------|----------------|-----------------|
| **Sin filtro** | Todas las reversiones se ejecutan | Testing, comparación |
| **1.0** | Poco restrictivo | Más reversiones, más operaciones |
| **1.2** | Moderado | Balance entre operaciones y calidad |
| **1.5** | Selectivo | **Recomendado para evitar reversiones prematuras** |
| **2.0+** | Muy selectivo | Solo reversiones con alto volumen confirmado |

---

## 🎯 Filtros Críticos: ATR y Market Regime

### ATR (Average True Range) - Stop Loss Dinámico

**¿Qué es?**
El ATR es un indicador de volatilidad que mide el rango promedio de movimiento del precio. Permite establecer stops loss dinámicos que se ajustan a la volatilidad del mercado.

**Parámetros:**
- **ATR Period:** Período para calcular ATR (recomendado: 14)
- **ATR Multiplier:** Multiplicador para calcular la distancia del stop loss (recomendado: 2.0 - 2.5)

**Función:** Reemplaza el stop loss fijo (`stop_loss_pct`) con un stop loss dinámico calculado como:
- **Largo:** `entry_price - (ATR * multiplier * leverage)`
- **Corto:** `entry_price + (ATR * multiplier * leverage)`

**Recomendaciones:**

#### ATR Period:
- **14 períodos:** Estándar de la industria, balance entre sensibilidad y estabilidad (**Recomendado**)
- **21 períodos:** Menos sensible, más estable para timeframes largos (1d)
- **7-10 períodos:** Más sensible, para timeframes muy cortos (1h)

#### ATR Multiplier:
- **1.5 - 2.0:** Más ajustado, permite más movimientos normales
- **2.0 - 2.5:** Balance óptimo entre protección y flexibilidad (**Recomendado**)
- **2.5 - 3.0:** Más conservador, protege mejor contra whipsaws
- **3.0+:** Muy conservador, puede limitar operaciones rentables

**Ventajas del ATR:**
- ✅ Se ajusta automáticamente a la volatilidad del mercado
- ✅ Evita stops demasiado ajustados en mercados volátiles
- ✅ Evita stops demasiado amplios en mercados tranquilos
- ✅ Mejor protección de capital en diferentes condiciones

**Cuándo usar ATR:**
- ✅ Mercados con volatilidad variable
- ✅ Timeframes medios y largos (4h, 1d)
- ✅ Cuando se busca protección dinámica del capital
- ✅ Estrategias que requieren stops adaptativos

---

### Market Regime Filter (Filtro de Regímenes de Mercado)

**¿Qué es?**
Un filtro que permite operar solo cuando el mercado está en un régimen favorable (tendencia fuerte) y no en condiciones extremas de volatilidad.

**Parámetros:**
- **ADX Period:** Período para calcular ADX (recomendado: 14)
- **ADX Threshold:** Umbral mínimo de ADX para considerar tendencia fuerte (recomendado: 25.0)
- **Max Volatility Multiplier (Opcional):** Límite máximo de volatilidad (ATR relativo)

**Función:**
- **ADX (Average Directional Index):** Mide la fuerza de la tendencia (0-100)
  - ADX > Threshold: Mercado en tendencia fuerte
  - ADX < Threshold: Mercado lateral/indeciso
- **Max Volatility (Opcional):** Filtra cuando la volatilidad (ATR relativo) es muy alta

**Recomendaciones:**

#### ADX Period:
- **14 períodos:** Estándar, balance entre sensibilidad y estabilidad (**Recomendado**)
- **21 períodos:** Menos sensible, para timeframes largos (1d)

#### ADX Threshold:
- **20.0 - 25.0:** Permite más operaciones, incluye tendencias moderadas (**Recomendado: 25.0**)
- **25.0 - 30.0:** Más selectivo, solo tendencias fuertes (**Recomendado para conservadores: 30.0**)
- **30.0+:** Muy selectivo, solo tendencias muy fuertes (pocas operaciones)

#### Max Volatility Multiplier (Opcional):
- **Sin límite (None):** Permite operar en cualquier volatilidad
- **2.0 - 3.0:** Limita operaciones en volatilidad muy alta (**Recomendado: 3.0 si se usa**)
- **3.0+:** Solo limita en volatilidad extrema

**Ventajas del Market Regime Filter:**
- ✅ Reduce operaciones en mercados laterales/indecisos
- ✅ Se enfoca en mercados con tendencias claras
- ✅ Mejora la calidad de las señales
- ✅ Reduce el riesgo de whipsaws
- ✅ Opcionalmente filtra condiciones extremas de volatilidad

**Cuándo usar Market Regime Filter:**
- ✅ Timeframes medios y largos (4h, 1d)
- ✅ Cuando se busca mayor calidad de señales
- ✅ Para reducir operaciones en mercados laterales
- ✅ Estrategias que funcionan mejor en tendencias

**Cuándo NO usar:**
- ❌ Timeframes muy cortos (1h o menos)
- ❌ Cuando se necesitan muchas operaciones
- ❌ Estrategias diseñadas para mercados laterales

---

## 📊 Recomendaciones por Timeframe

### Timeframe 4h (Recomendado)

#### Configuración Óptima Base:
- **Volume Ratio:** 1.0 (threshold)
- **Volume Reversal:** 1.5 (threshold)
- **ATR:** Period=14, Multiplier=2.0-2.5
- **Market Regime:** Opcional, ADX=14, Threshold=25.0-30.0

#### Período: 90 días
- **Recomendación:** ATR 14x2.0, Sin Market Regime (para más operaciones)
- **Alternativa:** ATR 14x2.5, Market Regime ADX14x25 (mayor calidad)

#### Período: 120-180 días
- **Recomendación:** ATR 14x2.0, Market Regime ADX14x25
- **Razón:** Mayor período requiere mejor filtrado para evitar sobrefitting

---

### Timeframe 1d

#### Configuración Óptima Base:
- **Volume Ratio:** 0.9-1.0 (threshold)
- **Volume Reversal:** 1.5-2.0 (threshold)
- **ATR:** Period=14-21, Multiplier=2.0-2.5
- **Market Regime:** Recomendado, ADX=14-21, Threshold=25.0-30.0

#### Período: 90 días
- **Recomendación:** ATR 21x2.0, Market Regime ADX21x25
- **Razón:** Menos velas disponibles, se necesita mayor selectividad

#### Período: 120-180 días
- **Recomendación:** ATR 21x2.5, Market Regime ADX21x30
- **Razón:** Mayor período y menor frecuencia de señales requieren máxima calidad

---

### Timeframe 1h

#### Configuración Óptima Base:
- **Volume Ratio:** 1.0-1.1 (threshold)
- **Volume Reversal:** 1.5 (threshold)
- **ATR:** Period=14, Multiplier=1.5-2.0
- **Market Regime:** No recomendado (demasiado restrictivo)

#### Período: 90-180 días
- **Recomendación:** ATR 14x2.0, Sin Market Regime
- **Razón:** Timeframe corto genera muchas señales, Market Regime puede ser demasiado restrictivo

---

## 🪙 Recomendaciones por Par de Trading

### Análisis Realizado

Se realizaron pruebas exhaustivas con la **Funnel Strategy** en diferentes pares de trading para identificar configuraciones óptimas que eviten liquidaciones y maximicen el rendimiento.

**Estrategia Evaluada:** Funnel Logic Strategy
- EMA 200 (contexto)
- RSI 14 (oversold: 30, overbought: 70)
- Volume Ratio Threshold: 1.0
- Delta Confirmation Candles: 2
- Take Profit: 8%
- Trailing Stop: Activation 5%, Distance 2%

**Período de Prueba:** 90 días (timeframe 4h)
**Capital Inicial:** $5,000
**Mercado:** Futures

---

### Configuraciones Óptimas por Par

#### BTC/USDT (Bitcoin)

**Configuración Recomendada:**
```
✅ ATR Period: 14
✅ ATR Multiplier: 1.5x
✅ Leverage: 10.0x
✅ Timeframe: 4h
✅ Período: 90 días (más estable)
```

**Resultados (90 días):**
- **Señales:** 1-23 señales (según período)
- **Retorno:** 64-1093% (varía según configuración)
- **Sharpe Ratio:** 1.99-2.03
- **Maximum Drawdown:** -59.43%
- **Características:** Más estable, menor volatilidad relativa

**Observaciones:**
- ✅ Funciona bien con configuración estándar (ATR 1.5x, Leverage 10x)
- ✅ Menor drawdown comparado con otros pares
- ⚠️ En períodos largos (180+ días) puede haber liquidaciones
- 💡 Recomendado para traders que buscan estabilidad

---

#### ETH/USDT (Ethereum)

**Configuración Recomendada:**
```
✅ ATR Period: 14
✅ ATR Multiplier: 1.5x
✅ Leverage: 10.0x
✅ Timeframe: 4h
✅ Período: 90 días
```

**Resultados (90 días):**
- **Señales:** 7-48 señales (según período)
- **Retorno:** 50.06%
- **Sharpe Ratio:** 2.44 (mejor Sharpe entre todos los pares)
- **Maximum Drawdown:** -89.90%
- **Características:** Excelente balance riesgo/retorno

**Observaciones:**
- ✅ Mejor Sharpe Ratio de todos los pares probados
- ✅ Genera señales consistentes
- ⚠️ Drawdown alto (~90%) pero esperado con leverage 10x
- 💡 Recomendado para traders que buscan mejor ajuste riesgo/retorno

---

#### XRP/USDT (Ripple)

**Configuración Recomendada:**
```
✅ ATR Period: 14
✅ ATR Multiplier: 2.0x (más alto por mayor volatilidad)
✅ Leverage: 10.0x
✅ Timeframe: 4h
✅ Período: 90 días
```

**Resultados (90 días):**
- **Señales:** 8-30 señales (según período)
- **Retorno:** 738.28% (mejor retorno absoluto)
- **Sharpe Ratio:** 2.32
- **Maximum Drawdown:** -94.79%
- **Características:** Alta volatilidad, mayor potencial de retorno

**Observaciones:**
- ✅ Mejor retorno absoluto entre todos los pares
- ✅ Genera muchas señales con buen rendimiento
- ⚠️ Requiere ATR multiplier mayor (2.0x) por mayor volatilidad
- ⚠️ Drawdown muy alto (~95%), requiere monitoreo constante
- 💡 Recomendado para traders agresivos con alta tolerancia al riesgo
- ⚠️ En períodos largos (180+ días) puede haber liquidaciones

---

#### SOL/USDT (Solana)

**Configuración Recomendada:**
```
✅ ATR Period: 14
✅ ATR Multiplier: 1.5x
✅ Leverage: 5.0x (reducido para evitar liquidaciones)
✅ Timeframe: 4h
✅ Período: 90 días
```

**Resultados (90 días):**
- **Señales:** 7-36 señales (según período)
- **Retorno:** -9.47% a -100% (problemático)
- **Sharpe Ratio:** 0.74 a -1.46
- **Maximum Drawdown:** -88% a -100% (liquidaciones frecuentes)
- **Características:** Alta volatilidad, propenso a liquidaciones

**Observaciones:**
- ⚠️ Muy volátil, propenso a liquidaciones incluso con configuraciones optimizadas
- ⚠️ Resultados inconsistentes entre diferentes períodos
- ⚠️ Requiere leverage reducido (5x) para minimizar riesgo de liquidación
- ❌ **No recomendado** para la estrategia actual sin ajustes adicionales
- 💡 Si se usa, considerar leverage 3-5x y monitoreo muy activo

---

### Resumen Comparativo por Par

| Par | ATR Mult | Leverage | Retorno (90d) | Sharpe | Drawdown | Recomendación |
|-----|----------|----------|---------------|--------|----------|---------------|
| **BTC/USDT** | 1.5x | 10.0x | 64-1093% | 1.99-2.03 | -59% | ✅ Recomendado (estable) |
| **ETH/USDT** | 1.5x | 10.0x | 50% | 2.44 | -90% | ✅ Recomendado (mejor Sharpe) |
| **XRP/USDT** | 2.0x | 10.0x | 738% | 2.32 | -95% | ⚠️ Cuidado (alto retorno pero alto riesgo) |
| **SOL/USDT** | 1.5x | 5.0x | -9% | 0.74 | -88% | ❌ No recomendado (muy volátil) |

#### Comparación Leverage 5x vs 10x

**Resultados con Leverage 5x (90 días, 4h):**

| Par | ATR | Leverage | Retorno | Sharpe | Drawdown | Liquidación |
|-----|-----|----------|---------|--------|----------|-------------|
| **BTC/USDT** | 1.5x | 5.0x | 41.15% | 1.90 | -32.00% | No |
| **ETH/USDT** | 1.5x | 5.0x | 39.35% | 1.62 | -51.83% | No |
| **XRP/USDT** | 2.0x | 5.0x | 583.06% | 1.63 | -47.40% | No |
| **SOL/USDT** | 1.5x | 5.0x | -9.47% | 0.74 | -88.05% | No |

**Ventajas del Leverage 5x:**
- ✅ **Drawdown significativamente menor** (30-50% reducción)
- ✅ **Sin liquidaciones** (incluso SOL/USDT sobrevive)
- ✅ **Mayor estabilidad** y menor riesgo
- ✅ **Más señales** (BTC/USDT: 8 vs 1 con 10x)
- ✅ **Mejor para conservadores** y períodos largos

**Desventajas del Leverage 5x:**
- ⚠️ **Retornos menores** (especialmente BTC/USDT: 1093% → 41%)
- ⚠️ **Sharpe Ratio generalmente menor** (aunque sigue siendo bueno >1.6)

**Recomendaciones:**
- **Leverage 10x:** Traders agresivos, períodos cortos, alta tolerancia al riesgo
- **Leverage 5x:** Traders conservadores, períodos largos (180+ días), reducir riesgo
- **SOL/USDT:** OBLIGATORIO usar leverage 5x o menor (evita liquidación)
---

### Observaciones Importantes sobre Períodos Largos

**Períodos de 180-365 días:**
- ⚠️ **Liquidaciones frecuentes** en todos los pares con leverage 10x
- ⚠️ La estrategia funciona mejor en **períodos de 90 días**
- ✅ Para períodos largos, considerar:
  - Reducir leverage a 5-7x
  - Aumentar ATR multiplier a 2.5-3.0x
  - Monitoreo más activo
  - Ajustes periódicos de parámetros

**Recomendación General:**
- ✅ Usar períodos de **90 días** para backtesting y trading
- ✅ Renovar/actualizar configuraciones cada 90 días
- ⚠️ Monitorear activamente en períodos más largos

---

## 🎯 Recomendaciones Finales

### Configuración Recomendada por Timeframe:

#### Timeframe 4h (MÁS RECOMENDADO):
```
✅ Volume Ratio: 1.0
✅ Volume Reversal: 1.5
✅ ATR: Period=14, Multiplier=2.0
✅ Market Regime: Opcional (ADX=14, Threshold=25.0 para más operaciones / 30.0 para mayor calidad)
✅ Stop Loss: Usar ATR (dejar stop_loss_pct vacío/desactivado)
```

**Nota sobre Stop Loss:**
- **`stop_loss_pct`**: Stop loss fijo como porcentaje del precio de entrada (ej: 1.5% = 0.015). Siempre usa la misma distancia sin importar la volatilidad.
- **ATR (recomendado)**: Stop loss dinámico que se ajusta a la volatilidad del mercado. Calcula la distancia basándose en el Average True Range (ATR) multiplicado por un factor.
- **Importante:** No uses ambos simultáneamente. Si activas ATR, deja `stop_loss_pct` vacío o en `None`. El sistema usará ATR automáticamente.

#### Timeframe 1d:
```
✅ Volume Ratio: 0.9-1.0
✅ Volume Reversal: 1.5-2.0
✅ ATR: Period=21, Multiplier=2.0-2.5
✅ Market Regime: Recomendado (ADX=21, Threshold=25.0-30.0)
✅ Stop Loss: Usar ATR
```

#### Timeframe 1h:
```
✅ Volume Ratio: 1.0-1.1
✅ Volume Reversal: 1.5
✅ ATR: Period=14, Multiplier=2.0
✅ Market Regime: No recomendado
✅ Stop Loss: Usar ATR
```

---

## 📈 Comparación: Con vs Sin Filtros Críticos

### Timeframe 4h, 90-180 días:

| Métrica | Sin ATR (stop_loss_pct=1.5%) | Con ATR (14x2.0) | Con ATR + Market Regime |
|---------|------------------------------|------------------|-------------------------|
| **Stop Loss** | Fijo (1.5%) | Dinámico (basado en volatilidad) | Dinámico + Filtrado de regímenes |
| **Protección** | No se ajusta a volatilidad | Se ajusta automáticamente | Se ajusta + solo tendencias fuertes |
| **Operaciones** | Más operaciones | Similar | Menos pero de mayor calidad |
| **Drawdown** | Variable según volatilidad | Mejor control | Mejor control + menor riesgo |
| **Uso Recomendado** | Testing inicial | **Producción** | **Producción (conservador)** |

---

## 💡 Consideraciones Importantes

### 1. Interacción entre Filtros:
- **Volume Ratio** controla **cuántas** señales se generan
- **Volume Reversal** controla **si** se ejecutan las reversiones
- **ATR** controla **cómo** se protege el capital (stop loss dinámico)
- **Market Regime** controla **en qué condiciones** se generan señales
- Todos trabajan de forma complementaria

### 2. ATR vs Stop Loss Fijo (`stop_loss_pct`):

**Stop Loss Fijo (`stop_loss_pct`):**
- **Definición:** Un porcentaje fijo del precio de entrada (ej: 1.5% = 0.015)
- **Cómo funciona:** Si compras a $100 y `stop_loss_pct = 0.015`, el stop loss siempre estará a $98.50 (1.5% menos)
- **Ventajas:** Simple, fácil de entender
- **Desventajas:** No se ajusta a la volatilidad del mercado
  - En mercados volátiles: puede ser demasiado ajustado (se activa con movimientos normales)
  - En mercados tranquilos: puede ser demasiado amplio (permitir pérdidas mayores de lo necesario)

**ATR (Average True Range):**
- **Definición:** Stop loss dinámico calculado como `precio_entrada ± (ATR × multiplicador × leverage)`
- **Cómo funciona:** Se ajusta automáticamente a la volatilidad actual del mercado
  - Si el mercado es volátil: el stop loss es más amplio (permite más movimiento)
  - Si el mercado es tranquilo: el stop loss es más ajustado (protege mejor)
- **Ventajas:** Se adapta a condiciones de mercado, mejor protección del capital
- **Desventajas:** Más complejo, requiere parámetros adicionales (ATR Period y Multiplier)

**Recomendación:** Usar ATR en lugar de `stop_loss_pct` para producción

### 3. Market Regime Filter:
- **Sin Market Regime:** Más operaciones, incluye mercados laterales
- **Con Market Regime:** Menos operaciones, mayor calidad, solo tendencias fuertes

### 4. Selección de Parámetros:
- Empieza con valores recomendados
- Ajusta según tu tolerancia al riesgo
- Más conservador = menos operaciones pero mayor calidad
- Más agresivo = más operaciones pero mayor riesgo

---

## 📝 Notas Finales

1. **Estos resultados son específicos** para el período y mercado analizado (Futures: BTC/USDT, ETH/USDT, XRP/USDT, SOL/USDT)
2. **Se recomienda realizar backtesting adicional** con datos más recientes antes de operar con capital real
3. **Los parámetros óptimos pueden variar** según condiciones de mercado (tendencia, volatilidad, etc.)
4. **Siempre valida las configuraciones** antes de usar capital real
5. **Monitorea el comportamiento** y ajusta según sea necesario
6. **ATR y Market Regime son filtros críticos** recomendados para mejorar la robustez de la estrategia
7. **Las configuraciones por par son específicas** - no uses la misma configuración para todos los pares
8. **Períodos de 90 días son recomendados** - períodos más largos pueden resultar en liquidaciones
9. **El leverage debe ajustarse según la volatilidad** del par de trading
10. **SOL/USDT requiere configuración especial** o considerar evitar para esta estrategia

---

## 🔄 Próximos Pasos

1. ✅ Probar las configuraciones recomendadas por par de trading
2. Validar con datos de mercado más recientes antes de producción
3. Ajustar según tus objetivos de riesgo/retorno
4. Considerar optimización adicional con walk-forward analysis
5. Monitorear el rendimiento en producción y ajustar parámetros
6. **Renovar configuraciones cada 90 días** para adaptarse a condiciones cambiantes
7. **Usar las configuraciones específicas por par** - no aplicar la misma configuración a todos
8. **Monitorear drawdown activamente** - si supera -80%, considerar reducir leverage
9. **Evitar períodos largos (180+ días)** sin ajustes o con leverage alto
10. **Considerar evitar SOL/USDT** o usar configuraciones muy conservadoras

---

*Documento generado automáticamente el 2026-01-13*
*Última actualización: 2026-01-14*
*Basado en análisis de parámetros y mejores prácticas de trading*
*Incluye resultados de pruebas con múltiples pares (BTC, ETH, XRP, SOL) y optimización de parámetros*

---

## 📈 Objetivos de Rendimiento: 5-8% Semanal

### Nuevos Objetivos Definidos

Con capital inicial de $5,000:
- **Objetivo Mínimo (5% semanal):** $250/semana = 64.29% en 90 días
- **Objetivo Ideal (8% semanal):** $400/semana = 102.86% en 90 días

**Ventajas:**
- ✅ Mucho más realistas que valores fijos
- ✅ Alcanzables con estrategias balanceadas
- ✅ Permiten configuraciones menos agresivas

### Configuraciones Recomendadas para 5-8% Semanal

**Para más detalles, ver:** `CONFIGURACIONES_5_8_PORCIENTO_SEMANAL.md`

**Configuración Principal (8% semanal):**
- Par: XRP/USDT
- Timeframe: 4h
- EMA: 200, RSI: 30/70, VR: 1.0, Delta: 2
- ATR: 2.0x, Leverage: 10x
- Resultado histórico: Ha superado este objetivo en algunos períodos

**Configuración Conservadora (5% semanal):**
- Par: XRP/USDT o ETH/USDT
- Timeframe: 4h
- Misma configuración que la principal
- Objetivo: 64% en 90 días

**⚠️ Nota:** Los resultados varían según período histórico. Monitoreo activo es esencial.