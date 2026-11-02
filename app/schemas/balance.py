from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel


class UserOwes(BaseModel):
    owes: Dict[str, float]


# The PDF assignment defines the primary balance output as:
# {
#   "Rahul": {
#     "owes": {
#       "Mohit": 400.0
#     }
#   }
# }
BalancesResponse = Dict[str, UserOwes]


class DetailedBalanceItem(BaseModel):
    debtor_id: int
    debtor_name: str
    creditor_id: int
    creditor_name: str
    amount: Decimal


class DetailedBalancesResponse(BaseModel):
    group_id: Optional[int] = None
    balances: List[DetailedBalanceItem]
