from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SettlementCreate(BaseModel):
    payer_id: int = Field(..., description="User ID of the person paying the debt")
    payee_id: int = Field(..., description="User ID of the person receiving the payment")
    amount: Decimal = Field(..., gt=0, description="Amount settled, must be greater than 0")
    group_id: Optional[int] = Field(None, description="Optional group context for the settlement")
    notes: Optional[str] = Field(None, max_length=255, description="Optional notes (e.g. UPI Ref / Cash)")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        return round(v, 2)


class SettlementResponse(BaseModel):
    id: int
    payer_id: int
    payer_name: str
    payee_id: int
    payee_name: str
    amount: Decimal
    group_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettlementSuggestion(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: Decimal


class SettlementSuggestionsResponse(BaseModel):
    group_id: Optional[int] = None
    total_transactions_before: int
    simplified_transactions_count: int
    suggestions: List[SettlementSuggestion]
