# Documentación: Funnel Logic Strategy

## Arquitectura de Lógica Jerárquica (Funnel Logic)

La estrategia `FunnelStrategy` implementa una arquitectura de tres etapas secuenciales con máquina de estados para reducir falsos positivos y mejorar la calidad de las señales.

---

## Pseudocódigo de la Máquina de Estados

```python
# ESTADO INICIAL: ESCANEO
estado = ESCANEO
setup_context = None

PARA cada vela i EN datos:
    
    SI estado == ESCANEO:
        # ETAPA 1: Determinar dirección del mercado
        dirección = check_trend(precio_cierre[i], EMA_200[i])
        
        SI dirección != NEUTRAL:
            estado = VIGILANCIA
            CONTINUAR
    
    SI estado == VIGILANCIA:
        # ETAPA 2: Detectar setup de retroceso débil
        dirección = check_trend(precio_cierre[i], EMA_200[i])
        
        SI dirección != NEUTRAL:
            setup_detectado = check_setup(dirección, RSI[i], Volume_Ratio[i])
            
            SI setup_detectado:
                setup_context = {
                    dirección: dirección,
                    índice_entrada: i,
                    velas_desde_setup: 0,
                    máximo_espera: 5
                }
                estado = ESPERANDO_CONFIRMACION
            SINO SI dirección == NEUTRAL:
                estado = ESCANEO  # Perdimos dirección
    
    SI estado == ESPERANDO_CONFIRMACION:
        setup_context.velas_desde_setup += 1
        
        # ETAPA 3: Confirmar con Volume Delta
        confirmado, razón = check_confirmation(
            setup_context.dirección,
            Delta[i],
            historial_delta,
            historial_precios,
            i
        )
        
        SI confirmado:
            # Ejecutar señal
            SI setup_context.dirección == LONG:
                señales[i] = 1  # COMPRA
            SINO SI setup_context.dirección == SHORT:
                señales[i] = -1  # VENTA
            
            estado = ESCANEO
            setup_context = None
        
        SINO SI setup_context.velas_desde_setup >= 5:
            # Timeout: cancelar setup
            estado = ESCANEO
            setup_context = None
        
        SINO SI check_trend(precio_cierre[i], EMA_200[i]) != setup_context.dirección:
            # Cambio de dirección, cancelar setup
            estado = ESCANEO
            setup_context = None
```

---

## Funciones Clave

### 1. `check_trend(close_price, ema_200)` → MarketDirection

**Etapa 1: Filtro de Contexto (ESCANEO)**

```python
FUNCIÓN check_trend(precio_cierre, EMA_200):
    SI precio_cierre > EMA_200:
        RETORNAR LONG
    SINO SI precio_cierre < EMA_200:
        RETORNAR SHORT
    SINO:
        RETORNAR NEUTRAL
```

**Objetivo:** Definir la dirección exclusiva del mercado. Solo buscar operaciones en la dirección determinada.

---

### 2. `check_setup(direction, rsi, volume_ratio)` → bool

**Etapa 2: Filtro de Gatillo/Setup (VIGILANCIA)**

```python
FUNCIÓN check_setup(dirección, RSI, Volume_Ratio):
    SI dirección == LONG:
        # Buscar sobreventa con volumen bajo
        SI RSI < 30 Y Volume_Ratio < 0.8:
            RETORNAR True  # Setup detectado
    
    SINO SI dirección == SHORT:
        # Buscar sobrecompra con volumen bajo
        SI RSI > 70 Y Volume_Ratio < 0.8:
            RETORNAR True  # Setup detectado
    
    RETORNAR False
```

**Objetivo:** Detectar retrocesos débiles en contra de la tendencia principal. Cuando se detecta, cambiar a estado `ESPERANDO_CONFIRMACION`.

**Lógica:**
- **Long Setup:** RSI < 30 (sobreventa) + Volume Ratio < 0.8 (volumen bajo en la caída)
- **Short Setup:** RSI > 70 (sobrecompra) + Volume Ratio < 0.8 (volumen bajo en el rebote)

---

### 3. `check_confirmation(direction, current_delta, delta_history, price_history, index)` → (bool, str)

**Etapa 3: Filtro de Confirmación (ESPERANDO_CONFIRMACION)**

```python
FUNCIÓN check_confirmation(dirección, Delta_actual, historial_delta, historial_precios, índice):
    
    SI dirección == LONG:
        # Confirmación 1: Delta positivo
        SI Delta_actual > 0:
            RETORNAR (True, "Delta positivo detectado")
        
        # Confirmación 2: Divergencia de Delta
        SI índice >= 3:
            delta_recientes = historial_delta[índice-3:índice+1]
            precios_recientes = historial_precios[índice-3:índice+1]
            
            delta_subiendo = delta_recientes[-1] > delta_recientes[0]
            precio_bajando = precios_recientes[-1] < precios_recientes[0]
            
            SI delta_subiendo Y precio_bajando:
                RETORNAR (True, "Divergencia de Delta detectada")
    
    SINO SI dirección == SHORT:
        # Confirmación 1: Delta negativo
        SI Delta_actual < 0:
            RETORNAR (True, "Delta negativo detectado")
        
        # Confirmación 2: Divergencia de Delta
        SI índice >= 3:
            delta_recientes = historial_delta[índice-3:índice+1]
            precios_recientes = historial_precios[índice-3:índice+1]
            
            delta_bajando = delta_recientes[-1] < delta_recientes[0]
            precio_subiendo = precios_recientes[-1] > precios_recientes[0]
            
            SI delta_bajando Y precio_subiendo:
                RETORNAR (True, "Divergencia de Delta detectada")
    
    RETORNAR (False, "Sin confirmación")
```

**Objetivo:** Entrar solo cuando hay flujo agresivo a favor de la tendencia.

**Confirmaciones válidas:**
1. **Delta directo:** Delta positivo (Long) o negativo (Short)
2. **Divergencia de Delta:** Precio se mueve en contra pero Delta se mueve a favor

**Timeout:** Si pasan 5 velas sin confirmación, cancelar el setup y volver a `ESCANEO`.

---

## Cálculo de Volume Delta

Como no tenemos acceso directo al order book, usamos una aproximación:

```python
FUNCIÓN calculate_volume_delta(datos):
    cambio_precio = precio_cierre.diff()
    cambio_precio_pct = cambio_precio / precio_cierre.shift(1)
    
    volumen_promedio = volumen.rolling(window=20).mean()
    volumen_normalizado = volumen / volumen_promedio
    
    # Delta aproximado: dirección del precio * volumen normalizado
    delta = cambio_precio_pct * volumen_normalizado * 1000
    
    RETORNAR delta
```

**Interpretación:**
- **Delta positivo:** Precio sube con volumen alto → Compra agresiva
- **Delta negativo:** Precio baja con volumen alto → Venta agresiva
- **Delta cercano a cero:** Movimiento con volumen bajo → Sin presión direccional

---

## Ejemplo de Uso

```python
from trading_bot import FunnelStrategy, DataHandler, Backtester

# 1. Crear estrategia con parámetros personalizados
strategy = FunnelStrategy(
    ema_period=200,              # EMA para contexto
    rsi_period=14,               # RSI para setup
    rsi_oversold=30.0,           # Umbral sobreventa
    rsi_overbought=70.0,         # Umbral sobrecompra
    volume_period=20,             # Período para volumen promedio
    volume_ratio_threshold=0.8,   # Umbral máximo de Volume Ratio
    delta_confirmation_candles=5, # Máximo de velas para confirmación
    delta_lookback=3              # Velas hacia atrás para análisis de Delta
)

# 2. Descargar datos
data_handler = DataHandler(symbol='BTC/USDT', market_type='futures')
data = data_handler.fetch_historical_data(timeframe='4h', days=180)

# 3. Generar señales
signals = strategy.generate_signals(data)

# 4. Ejecutar backtest
backtester = Backtester(
    initial_capital=5000.0,
    commission=0.001,
    leverage=10.0,
    market_type='futures',
    atr_period=14,
    atr_multiplier=2.0
)

results = backtester.run_backtest(data, signals)
metrics = backtester.calculate_metrics(results, timeframe='4h')
```

---

## Flujo de Estados

```
┌─────────────┐
│   ESCANEO   │ ← Estado inicial, busca dirección del mercado
└──────┬──────┘
       │
       │ EMA 200 determina dirección (LONG/SHORT)
       ▼
┌─────────────┐
│  VIGILANCIA │ ← Busca setup: RSI < 30 (Long) o > 70 (Short) + Volume Ratio < 0.8
└──────┬──────┘
       │
       │ Setup detectado
       ▼
┌──────────────────────────┐
│ ESPERANDO_CONFIRMACION   │ ← Espera confirmación de Delta (máx 5 velas)
└──────┬───────────────────┘
       │
       │ Delta positivo (Long) o negativo (Short) O Divergencia detectada
       ▼
┌─────────────┐
│  EJECUCION  │ ← Señal ejecutada (1 = Long, -1 = Short)
└──────┬──────┘
       │
       │ Reset
       ▼
┌─────────────┐
│   ESCANEO   │ ← Volver a buscar nueva oportunidad
└─────────────┘
```

---

## Ventajas de la Arquitectura Funnel Logic

1. **Reducción de Falsos Positivos:** Las tres etapas filtran progresivamente las señales
2. **Mayor Calidad:** Solo entra cuando hay confirmación de flujo agresivo
3. **Adaptabilidad:** Se ajusta automáticamente a la dirección del mercado
4. **Control de Riesgo:** Timeout automático si no hay confirmación en 5 velas
5. **Claridad:** Cada etapa tiene un propósito específico y medible

---

## Parámetros Configurables

| Parámetro | Descripción | Valor por Defecto |
|-----------|-------------|-------------------|
| `ema_period` | Período para EMA de contexto | 200 |
| `rsi_period` | Período para cálculo de RSI | 14 |
| `rsi_oversold` | Umbral RSI para sobreventa | 30.0 |
| `rsi_overbought` | Umbral RSI para sobrecompra | 70.0 |
| `volume_period` | Período para promedio de volumen | 20 |
| `volume_ratio_threshold` | Umbral máximo de Volume Ratio | 0.8 |
| `delta_confirmation_candles` | Máximo de velas para confirmación | 5 |
| `delta_lookback` | Velas hacia atrás para análisis Delta | 3 |

---

## Notas Importantes

1. **Volume Delta Aproximado:** Sin acceso al order book, el Delta se calcula usando precio y volumen. Para mayor precisión, considera integrar datos de order flow real.

2. **Timeframe Recomendado:** La estrategia funciona mejor en timeframes medios (4h, 1d) donde las señales tienen más tiempo para desarrollarse.

3. **Validación de Datos:** La estrategia requiere columnas `close`, `high`, `low`, `volume` en el DataFrame.

4. **Compatibilidad:** La estrategia es compatible con el sistema de backtesting existente y puede usarse con `Backtester` sin modificaciones.

---

*Documentación generada para FunnelStrategy v1.0.0*
