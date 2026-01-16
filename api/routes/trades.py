"""
Rutas para gestión de operaciones (trades).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import func

from database.database import get_db
from database.models import Trade, TradeType, ExitReason
from api.schemas import TradeSchema, TradeStatsSchema

router = APIRouter()


@router.get("/", response_model=List[TradeSchema])
def list_trades(
    backtest_id: int = Query(..., description="ID del backtest"),
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Listar operaciones de un backtest."""
    trades = (
        db.query(Trade)
        .filter(Trade.backtest_run_id == backtest_id)
        .order_by(Trade.fecha_entrada)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return trades


@router.get("/{trade_id}", response_model=TradeSchema)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Obtener detalle de una operación."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    return trade


@router.get("/stats/summary", response_model=TradeStatsSchema)
def get_trade_stats(
    backtest_id: int = Query(..., description="ID del backtest"),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas agregadas de operaciones."""
    trades = db.query(Trade).filter(Trade.backtest_run_id == backtest_id).all()
    
    if not trades:
        raise HTTPException(status_code=404, detail="No se encontraron operaciones para este backtest")
    
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.pnl_dollar > 0]
    losing_trades = [t for t in trades if t.pnl_dollar < 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    
    total_pnl = sum(t.pnl_dollar for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
    
    avg_win = sum(t.pnl_dollar for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
    avg_loss = sum(t.pnl_dollar for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
    
    total_wins = sum(t.pnl_dollar for t in winning_trades)
    total_losses = abs(sum(t.pnl_dollar for t in losing_trades))
    profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0.0)
    
    largest_win = max((t.pnl_dollar for t in trades), default=0.0)
    largest_loss = min((t.pnl_dollar for t in trades), default=0.0)
    
    return TradeStatsSchema(
        total_trades=total_trades,
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_pnl=avg_pnl,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        largest_win=largest_win,
        largest_loss=largest_loss,
    )
