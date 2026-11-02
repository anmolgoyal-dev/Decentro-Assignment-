from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.balance import DetailedBalanceItem, DetailedBalancesResponse
from app.services.balance_service import get_structured_balances, get_detailed_balances

router = APIRouter(prefix="/balances", tags=["Balances"])


@router.get("")
def get_all_balances(
    group_id: Optional[int] = Query(None, description="Optional group filter"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns balances in the structured JSON format specified in the PDF assignment:
    {
      "Rahul": {
        "owes": {
          "Mohit": 400.0
        }
      },
      "Ankit": {
        "owes": {
          "Mohit": 400.0
        }
      }
    }
    """
    return get_structured_balances(db, group_id=group_id)


@router.get("/detailed", response_model=DetailedBalancesResponse)
def get_detailed_balance_list(
    group_id: Optional[int] = Query(None, description="Optional group filter"),
    db: Session = Depends(get_db)
):
    """
    Returns a normalized list of pairwise debts including user IDs and Decimal amounts.
    """
    items: List[DetailedBalanceItem] = get_detailed_balances(db, group_id=group_id)
    return DetailedBalancesResponse(
        group_id=group_id,
        balances=items
    )
