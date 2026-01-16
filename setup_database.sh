#!/bin/bash
# Script para configurar la base de datos PostgreSQL

echo "=== Configuración de Base de Datos PostgreSQL ==="
echo ""

# Verificar si PostgreSQL está instalado
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL no está instalado. Por favor instálalo primero:"
    echo "   sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

echo "✓ PostgreSQL cliente encontrado"
echo ""

# Configuración por defecto
DB_NAME="trading_db"
DB_USER="trading_user"
DB_PASSWORD="trading_pass"

echo "Configuración de base de datos:"
echo "  - Nombre: $DB_NAME"
echo "  - Usuario: $DB_USER"
echo "  - Password: $DB_PASSWORD"
echo ""

# Solicitar confirmación
read -p "¿Continuar con esta configuración? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operación cancelada."
    exit 1
fi

# Crear base de datos y usuario (requiere permisos de postgres)
echo ""
echo "Creando base de datos y usuario..."
echo "NOTA: Esto requiere ejecutarse como usuario postgres o con sudo"
echo ""

# Comandos SQL
SQL_COMMANDS=$(cat <<EOF
-- Crear usuario si no existe
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- Crear base de datos si no existe
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Otorgar privilegios
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Conectar a la base de datos y otorgar privilegios en el esquema public
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF
)

# Intentar ejecutar como usuario actual, luego como postgres
if psql -U $USER -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo "$SQL_COMMANDS" | psql -U $USER -d postgres
    echo "✓ Base de datos y usuario creados"
elif sudo -u postgres psql -c "SELECT 1" > /dev/null 2>&1; then
    echo "$SQL_COMMANDS" | sudo -u postgres psql
    echo "✓ Base de datos y usuario creados"
else
    echo ""
    echo "⚠ No se pudo ejecutar automáticamente. Ejecuta manualmente:"
    echo ""
    echo "sudo -u postgres psql <<EOF"
    echo "$SQL_COMMANDS"
    echo "EOF"
    echo ""
    exit 1
fi

echo ""
echo "✓ Base de datos configurada correctamente"
echo ""
echo "Próximos pasos:"
echo "1. Configura DATABASE_URL en .env (o variable de entorno)"
echo "2. Ejecuta: alembic upgrade head"
echo ""
