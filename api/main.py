"""
Aplicación FastAPI principal.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import backtests, trades, signals

app = FastAPI(
    title="Trading Bot API",
    description="API REST para backtesting de trading bot",
    version="1.0.0"
)

# Configurar CORS para permitir conexiones desde el dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {"message": "Trading Bot API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
