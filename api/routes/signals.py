"""
Rutas para gestión de señales.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from database.models import Signal
from api.schemas import SignalSchema

router = APIRouter()


@router.get("/", response_model=List[SignalSchema])
def list_signals(
    backtest_id: int = Query(..., description="ID del backtest"),
    signal_type: str = Query(None, description="Filtrar por tipo de señal (BUY/SELL/HOLD)"),
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db)
):
    """Listar señales de un backtest."""
    query = db.query(Signal).filter(Signal.backtest_run_id == backtest_id)
    
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    
    signals = query.order_by(Signal.timestamp).offset(skip).limit(limit).all()
    return signals


@router.get("/{signal_id}", response_model=SignalSchema)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Obtener detalle de una señal."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    return signal
