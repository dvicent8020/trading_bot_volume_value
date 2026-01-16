# Setup de Base de Datos y Dashboard

## Requisitos Previos

1. PostgreSQL instalado y corriendo
2. Python 3.8+

## Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Base de Datos

Crear base de datos PostgreSQL:

```bash
createdb trading_db
# O usando psql:
# psql -U postgres
# CREATE DATABASE trading_db;
# CREATE USER trading_user WITH PASSWORD 'trading_pass';
# GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
```

### 3. Configurar variables de entorno

Crear archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL
```

### 4. Ejecutar migraciones

```bash
# Crear migración inicial
alembic revision --autogenerate -m "Initial schema"

# Aplicar migraciones
alembic upgrade head
```

## Uso

### Iniciar API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Iniciar Dashboard

```bash
python dashboard/app.py
# O:
# python -m dashboard.app
```

El dashboard estará disponible en: http://localhost:8050
La API estará disponible en: http://localhost:8000

## Estructura de Base de Datos

- `backtest_runs`: Ejecuciones de backtest
- `strategy_configs`: Configuraciones de estrategia
- `trades`: Operaciones individuales
- `signals`: Señales generadas
- `market_data`: Datos OHLCV (opcional)

## API Endpoints

- `GET /api/backtests/` - Listar backtests
- `POST /api/backtests/run` - Ejecutar nuevo backtest
- `GET /api/backtests/{id}` - Detalle de backtest
- `GET /api/trades/?backtest_id={id}` - Operaciones de un backtest
- `GET /api/signals/?backtest_id={id}` - Señales de un backtest
