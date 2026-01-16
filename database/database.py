"""
Configuración de base de datos PostgreSQL usando SQLAlchemy.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

# URL de conexión a la base de datos desde variable de entorno
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trading_user:trading_pass@localhost/trading_db"
)

# Crear motor de base de datos
engine = create_engine(DATABASE_URL, echo=False)

# SessionLocal para crear sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos declarativos
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependencia para obtener sesión de base de datos.
    
    Yields:
        Sesión de base de datos SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
