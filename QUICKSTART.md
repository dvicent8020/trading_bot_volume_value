# Guía Rápida de Inicio

## Prerequisitos

- Python 3.8+
- PostgreSQL instalado
- pip3

## Instalación Rápida

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Base de Datos PostgreSQL

**Opción A: Script automático (Linux/Mac)**

```bash
./setup_database.sh
```

**Opción B: Manual**

```bash
# Como usuario postgres
sudo -u postgres psql

# En psql:
CREATE USER trading_user WITH PASSWORD 'trading_pass';
CREATE DATABASE trading_db;
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
\c trading_db
GRANT ALL ON SCHEMA public TO trading_user;
\q
```

### 3. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales si es necesario
# DATABASE_URL=postgresql://trading_user:trading_pass@localhost/trading_db
```

O exportar directamente:

```bash
export DATABASE_URL="postgresql://trading_user:trading_pass@localhost/trading_db"
```

### 4. Ejecutar migraciones

```bash
# Crear migración inicial (si no existe)
alembic revision --autogenerate -m "Initial schema"

# Aplicar migraciones
alembic upgrade head
```

### 5. Iniciar Servicios

**Terminal 1: API FastAPI**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en: http://localhost:8000
Documentación interactiva: http://localhost:8000/docs

**Terminal 2: Dashboard Dash**

```bash
python dashboard/app.py
```

El dashboard estará disponible en: http://localhost:8050

## Uso

1. Abre el navegador en http://localhost:8050
2. Ve a la pestaña "Configuración"
3. Configura los parámetros del backtest
4. Haz clic en "Ejecutar Backtest"
5. Ve a la pestaña "Backtests" para ver el progreso
6. Una vez completado, puedes ver resultados, operaciones y señales

## Estructura de URLs

- **Dashboard**: http://localhost:8050
- **API REST**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## Solución de Problemas

### Error: "No module named 'psycopg2'"

```bash
pip install psycopg2-binary
```

### Error: "Connection refused" (PostgreSQL)

- Verifica que PostgreSQL esté corriendo: `sudo systemctl status postgresql`
- Inicia PostgreSQL: `sudo systemctl start postgresql`
- Verifica que el usuario y base de datos existan

### Error: "Target database is not up to date"

```bash
# Ver estado de migraciones
alembic current

# Aplicar todas las migraciones pendientes
alembic upgrade head
```

### Error en Dashboard: "Error cargando backtests"

- Verifica que la API esté corriendo en http://localhost:8000
- Verifica la URL en `dashboard/app.py` (línea 18): `API_URL = "http://localhost:8000"`
