from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.settlement import Settlement
from app.models.user import User
from app.schemas.settlement import (
    SettlementCreate,
    SettlementResponse,
    SettlementSuggestionsResponse,
)
from app.services.settlement_service import record_settlement, simplify_debts_min_cash_flow

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def create_settlement(settlement_in: SettlementCreate, db: Session = Depends(get_db)):
    """
    Record a debt settlement payment between two users.
    Reduces the net balance between the payer and the payee.
    """
    return record_settlement(db, settlement_in)


@router.get("", response_model=List[SettlementResponse])
def list_settlements(
    group_id: Optional[int] = Query(None, description="Optional group filter"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List past settlement transactions.
    """
    query = db.query(Settlement)
    if group_id is not None:
        query = query.filter(Settlement.group_id == group_id)

    settlements = query.order_by(Settlement.created_at.desc()).offset(skip).limit(limit).all()

    all_users = {u.id: u.name for u in db.query(User).all()}

    return [
        SettlementResponse(
            id=s.id,
            payer_id=s.payer_id,
            payer_name=all_users.get(s.payer_id, f"User_{s.payer_id}"),
            payee_id=s.payee_id,
            payee_name=all_users.get(s.payee_id, f"User_{s.payee_id}"),
            amount=s.amount,
            group_id=s.group_id,
            notes=s.notes,
            created_at=s.created_at
        )
        for s in settlements
    ]


@router.get("/suggestions", response_model=SettlementSuggestionsResponse)
def get_settlement_suggestions(
    group_id: Optional[int] = Query(None, description="Optional group filter"),
    db: Session = Depends(get_db)
):
    """
    Smart settlement suggestions computed using the Min-Cash-Flow graph algorithm.
    Minimizes the total number of interpersonal payment transactions required to settle all debts.
    """
    return simplify_debts_min_cash_flow(db, group_id=group_id)
